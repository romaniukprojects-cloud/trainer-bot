# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Telegram bot for a personal fitness trainer to track 10-session client packages. Clients pay per package (valid 1 month); unused sessions expire. The bot handles attendance marking, package consumption, payment reminders, and a client self-service interface — all in Ukrainian.

Full implementation plan: `~/.claude/plans/modular-singing-valiant.md`

## Commands

```bash
# Install dependencies
uv sync                          # or: pip install -e ".[dev]"

# Run bot locally (without Docker)
python -m app.main

# Docker (recommended for deployment)
docker compose up --build
docker compose down

# Database migrations
alembic upgrade head             # apply all migrations
alembic revision --autogenerate -m "description"  # create new migration

# Tests
pytest                           # all tests
pytest tests/test_packages.py    # single file
pytest -k "test_fifo"            # single test by name

# Lint / format
ruff check .
ruff format .
```

## Architecture

**Entry point:** `app/main.py` — wires together the aiogram Bot/Dispatcher, SQLAlchemy async engine, APScheduler, and registers all routers.

**Layer separation (critical):**
- `app/services/` — all business logic, zero aiogram imports. Directly testable. Would work with a FastAPI frontend without changes.
- `app/bot/handlers/` — thin aiogram handlers; they call services and format responses. No business logic here.
- `app/scheduler/jobs/` — scheduled tasks that call services.
- `app/db/repositories/` — raw DB queries only; no business logic.

**Domain flow — marking attendance (free text):**
1. Trainer sends free text (any message not in FSM state) → `bot/handlers/trainer/quick_mark.py`
2. `services/name_parser.py::parse_text()` → tokenizes by comma/newline first, then tries space-splitting greedily (2-word, then 1-word) for unmatched tokens
3. Fuzzy-match via RapidFuzz `WRatio`, threshold 80, against `clients.full_name` + `clients.aliases`
4. Skip keywords: "не була/не був/не прийшов/пропуск/🚫" → `missed_no_notice` status
5. Ambiguous (2+ matches) → inline keyboard to resolve one-by-one; unrecognized → flagged in summary
6. Trainer confirms summary → `services/sessions.py::mark_attended()` per client
7. `mark_attended()` checks idempotency first: if countable session already exists for client on same calendar day (Kyiv time) → skips, returns `is_duplicate=True`
8. FIFO package selection (`services/packages.py::find_active_for_consumption()`) — consumes the package expiring soonest first

**Session statuses:** `pending_confirmation | attended | missed_no_notice | cancelled_in_advance | cancelled_by_trainer`
- `missed_no_notice` — client didn't show, no warning → **counts** against the package
- `cancelled_in_advance` — client warned ahead of time → **does not count**

**Package lifecycle:** `active → exhausted` (10 sessions used) or `active → expired` (expires_at passed). Nightly job at 00:05 Kyiv handles both transitions. `expires_at` is always `purchased_at + relativedelta(months=1)` (not `timedelta(days=30)`).

**Scheduler jobs** (`app/scheduler/jobs/`):
| Job | Schedule | Purpose |
|---|---|---|
| `expire_packages` | nightly 00:05 | mark exhausted/expired packages |
| `prepare_auto_sessions` | nightly 01:00 | create `pending_confirmation` sessions 7 days ahead |
| `confirmation_reminder` | hourly | send trainer inline buttons 1h before each session |
| `auto_finalize` | every 30 min | auto-mark as `attended` if no trainer response within 4h |
| `payment_reminder` | one-shot (+1h) | triggered from `mark_attended` on 9th session |

APScheduler uses `SQLAlchemyJobStore` (same SQLite DB) — jobs survive restarts. Set `misfire_grace_time=3600, coalesce=True`.

**Auth:** `app/bot/middlewares/auth.py` gates all handlers — trainer access by `TRAINER_TELEGRAM_ID` from `.env`; client access by `telegram_user_id` match in `clients` table.

**Client linking:** trainer runs "Додати клієнта" → bot generates 6-char `link_code` (24h TTL) → trainer forwards `t.me/<bot>?start=<code>` to client → client clicks → `/start <code>` populates `clients.telegram_user_id`. Clients without Telegram remain NULL and are managed manually by the trainer.

**Timezone:** store everything as UTC in DB; convert at the boundary using `app/utils/tz.py::to_kyiv()` / `to_utc()`. Use `dateutil.relativedelta` everywhere dates are added to months.

**All UI strings** are in `app/bot/texts.py` — never hardcode Ukrainian text in handlers.

## Current Status

**Phase 0 — complete.** Bootstrap: all DB models, migration, Docker, config, `/start`.

**Phase 1 — complete.** Manual MVP: add client, register payment (with backdated date), mark sessions via menu (multi-select), client overview, link_code flow, client balance/history. Delete client feature added.

**Phase 1.5 — complete.** Fast text marking: `services/name_parser.py` (fuzzy RapidFuzz WRatio, threshold 80), space-separated + comma/newline tokenization, skip keyword detection, disambiguation flow, confirm-before-save summary, per-day idempotency guard in `mark_attended`. Menu buttons excluded from the free-text handler.

**Payment date**: register payment handler asks [📅 Сьогодні / ✏️ Інша дата]; accepts DD.MM or DD.MM.YYYY; `purchased_at` passed to `register_payment()`; `expires_at = purchased_at + relativedelta(months=1)`.

**Phase 2 — complete.** Extended trainer features:
- **Sessions by date** (`bot/handlers/trainer/sessions_by_date.py`) — trainer picks 📅 Сьогодні or enters DD.MM / DD.MM.YYYY; shows all sessions for that day with emoji status and package progress (e.g. `5/10`).
- **Schedule management** (`bot/handlers/trainer/schedule.py`) — trainer assigns recurring weekly slots (weekday + HH:MM) per client; slots stored in `schedule_slots` table; can add/remove slots via inline keyboard.
- **Client history** (`bot/handlers/client/history.py`) — client can view last 20 sessions with date, weekday, and status label via menu or `/history` command.
- **Payment reminder to client** — after 9th session, bot sends client a reminder message about upcoming package renewal.
- **trainers table + migration 0002** — `db/models/trainer.py` and `db/repositories/trainers.py` added for future multi-trainer support; migration applied.

**Phase 3 — complete.** All scheduler jobs implemented:
- `expire_packages.py` — nightly 00:05 Kyiv: marks packages as `exhausted` (10 sessions used) or `expired` (past `expires_at`)
- `prepare_auto_sessions.py` — nightly 01:00: creates `pending_confirmation` sessions 7 days ahead from `schedule_slots`
- `confirmation_reminder.py` — hourly: sends trainer inline buttons [✅ прийшов / 🚫 пропуск] 1h before each scheduled session
- `auto_finalize.py` — every 30 min: auto-marks as `attended` if trainer hasn't responded within 4h
- `payment_reminder.py` — one-shot +1h: triggered from `mark_attended` on the 9th session

**Auto-session confirm flow**: trainer taps inline button from any context → `sched_confirm:<session_id>:<attended|missed>` callback → `services/schedule.py::confirm_session()` → updates status and consumes package; reply shows name + package usage.

**Next:** no planned phases — bot is feature-complete for solo trainer use.

## Environment

```
BOT_TOKEN=                # from @BotFather
TRAINER_TELEGRAM_ID=      # your Telegram numeric user ID
DATABASE_URL=sqlite+aiosqlite:///./data/clients.db
TIMEZONE=Europe/Kyiv
```

Copy `.env.example` → `.env` before running.
