from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import texts
from app.bot.keyboards.inline import date_choice_kb, disambiguate_kb, quick_multi_kb
from app.bot.keyboards.trainer_menu import (
    BTN_ADD_CLIENT,
    BTN_CANCEL_TRAINING,
    BTN_CORRECTIONS,
    BTN_DELETE_CLIENT,
    BTN_INCOME,
    BTN_INVITE_LINK,
    BTN_MARK_SESSION,
    BTN_OVERVIEW,
    BTN_PAYMENT_DETAILS,
    BTN_REGISTER_PAYMENT,
    BTN_SCHEDULE,
    BTN_SESSIONS_BY_DATE,
    trainer_main_kb,
)
from app.bot.states.trainer import QuickMarkStates
from app.config import settings
from app.db.models.client import Client
from app.db.models.session_record import SessionStatus
from app.db.repositories import audit_log as audit_repo
from app.db.repositories.clients import get_by_id
from app.services.clients import get_active_clients
from app.services.name_parser import parse_text
from app.services.sessions import mark_attended
from app.utils.tz import now_kyiv

router = Router()

_STATUS_KEY = {
    SessionStatus.attended: "attended",
    SessionStatus.missed_no_notice: "missed",
}
_STATUS_MAP = {
    "attended": SessionStatus.attended,
    "missed": SessionStatus.missed_no_notice,
}
_STATUS_LABELS = {
    "attended": "✅ прийшов",
    "missed": "🚫 пропуск",
}

_CYCLE = {
    None: "attended",
    "attended": "missed",
    "missed": None,
}

_MENU_BUTTONS = {
    BTN_ADD_CLIENT,
    BTN_REGISTER_PAYMENT,
    BTN_MARK_SESSION,
    BTN_OVERVIEW,
    BTN_SESSIONS_BY_DATE,
    BTN_DELETE_CLIENT,
    BTN_PAYMENT_DETAILS,
    BTN_SCHEDULE,
    BTN_CANCEL_TRAINING,
    BTN_CORRECTIONS,
    BTN_INCOME,
    BTN_INVITE_LINK,
}


def _parse_date(text: str) -> datetime | None:
    tz = ZoneInfo(settings.timezone)
    today = now_kyiv().date()
    for fmt in ("%d.%m.%Y", "%d.%m"):
        try:
            parsed = datetime.strptime(text.strip(), fmt)
            if fmt == "%d.%m.%Y":
                d = parsed.date()
            else:
                d = today.replace(month=parsed.month, day=parsed.day)
                if d > today:
                    d = d.replace(year=d.year - 1)
            return datetime(d.year, d.month, d.day, 12, 0, tzinfo=tz).astimezone(UTC)
        except ValueError:
            continue
    return None


# ─── Date entry for quick mark (must be BEFORE absorb_text_in_dialog) ────────

@router.message(QuickMarkStates.enter_date)
async def got_date_qm(message: Message, state: FSMContext, session: AsyncSession) -> None:
    occurred_at = _parse_date(message.text or "")
    if occurred_at is None:
        await message.answer(texts.INVALID_DATE)
        return
    data = await state.get_data()
    resolved: list[dict] = data["resolved"]
    lines = await _build_lines(session, resolved, occurred_at)
    await state.clear()
    summary = "✅ <b>Збережено:</b>\n\n" + "".join(lines) if lines else texts.CANCEL_ACTION
    await message.answer(summary, reply_markup=trainer_main_kb)


# ─── Catch-all for text while any FSM is active ──────────────────────────────

@router.message(~StateFilter(None), F.text, ~F.text.startswith("/"), ~F.text.in_(_MENU_BUTTONS))
async def absorb_text_in_dialog(message: Message, is_trainer: bool) -> None:
    if not is_trainer:
        return


@router.message(StateFilter(None), F.text, ~F.text.startswith("/"), ~F.text.in_(_MENU_BUTTONS))
async def handle_free_text(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    is_trainer: bool,
) -> None:
    if not is_trainer:
        return

    clients = await get_active_clients(session)
    if not clients:
        await message.answer(texts.NO_ACTIVE_CLIENTS)
        return

    entries = parse_text(message.text, clients)
    if not any(e.matches for e in entries):
        await message.answer(texts.QUICK_MARK_NO_MATCH)
        return

    resolved: list[dict] = []
    pending: list[dict] = []
    unrecognized: list[str] = []

    for entry in entries:
        if entry.is_resolved:
            c = entry.matches[0]
            resolved.append({
                "client_id": c.id,
                "status": _STATUS_KEY.get(entry.status, "attended"),
                "name": c.full_name,
            })
        elif entry.is_ambiguous:
            pending.append({
                "token": entry.clean_name,
                "candidate_ids": [c.id for c in entry.matches],
                "candidate_names": [c.full_name for c in entry.matches],
                "status": _STATUS_KEY.get(entry.status, "attended"),
            })
        else:
            unrecognized.append(entry.token)

    await state.update_data(resolved=resolved, pending=pending, unrecognized=unrecognized)

    if pending:
        await state.set_state(QuickMarkStates.disambiguating)
        await _ask_disambiguation(message, pending[0])
    else:
        await state.set_state(QuickMarkStates.confirming)
        await _show_multi_select(message, resolved, unrecognized)


async def _ask_disambiguation(msg_or_cb: Message | CallbackQuery, item: dict) -> None:
    text = texts.QUICK_MARK_AMBIGUOUS.format(token=item["token"])
    kb = disambiguate_kb(item["candidate_ids"], item["candidate_names"])
    if isinstance(msg_or_cb, Message):
        await msg_or_cb.answer(text, reply_markup=kb)
    else:
        await msg_or_cb.message.edit_text(text, reply_markup=kb)


async def _show_multi_select(
    msg_or_cb: Message | CallbackQuery,
    resolved: list[dict],
    unrecognized: list[str],
    edit: bool = False,
) -> None:
    selections = {str(item["client_id"]): item["status"] for item in resolved}
    names = {str(item["client_id"]): item["name"] for item in resolved}

    header = "📋 <b>Відмітити заняття:</b>\n\nТапни на ім'я — змінить статус по колу."
    if unrecognized:
        header += "\n\n❓ <b>Не розпізнано:</b> " + ", ".join(f"«{t}»" for t in unrecognized)

    kb = quick_multi_kb(selections, names)
    if edit and isinstance(msg_or_cb, CallbackQuery):
        await msg_or_cb.message.edit_text(header, reply_markup=kb)
    elif isinstance(msg_or_cb, Message):
        await msg_or_cb.answer(header, reply_markup=kb)
    else:
        await msg_or_cb.message.edit_text(header, reply_markup=kb)


@router.callback_query(QuickMarkStates.disambiguating, F.data.startswith("disambig:"))
async def resolve_ambiguity(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    data = await state.get_data()
    pending: list[dict] = data["pending"]
    resolved: list[dict] = data["resolved"]
    unrecognized: list[str] = data["unrecognized"]
    current = pending[0]

    choice = callback.data.split(":")[1]
    if choice != "skip":
        client: Client | None = await get_by_id(session, int(choice))
        if client:
            resolved.append({
                "client_id": client.id,
                "status": current["status"],
                "name": client.full_name,
            })
    else:
        unrecognized.append(current["token"])

    pending = pending[1:]
    await state.update_data(resolved=resolved, pending=pending, unrecognized=unrecognized)
    await callback.answer()

    if pending:
        await _ask_disambiguation(callback, pending[0])
    else:
        await state.set_state(QuickMarkStates.confirming)
        await _show_multi_select(callback, resolved, unrecognized, edit=True)


@router.callback_query(QuickMarkStates.confirming, F.data.startswith("qm_toggle:"))
async def toggle_status(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()

    data = await state.get_data()
    resolved: list[dict] = data["resolved"]
    unrecognized: list[str] = data.get("unrecognized", [])

    cid_str = callback.data.split(":")[1]
    for item in resolved:
        if str(item["client_id"]) == cid_str:
            item["status"] = _CYCLE[item["status"]]
            break

    await state.update_data(resolved=resolved)

    selections = {str(item["client_id"]): item["status"] for item in resolved}
    names = {str(item["client_id"]): item["name"] for item in resolved}

    header = "📋 <b>Відмітити заняття:</b>\n\nТапни на ім'я — змінить статус по колу."
    if unrecognized:
        header += "\n\n❓ <b>Не розпізнано:</b> " + ", ".join(f"«{t}»" for t in unrecognized)

    try:
        await callback.message.edit_text(header, reply_markup=quick_multi_kb(selections, names))
    except TelegramBadRequest:
        pass


@router.callback_query(QuickMarkStates.confirming, F.data == "qm_save")
async def ask_date_qm(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(QuickMarkStates.choosing_date)
    try:
        await callback.message.edit_text(texts.SESSION_ASK_DATE, reply_markup=date_choice_kb())
    except TelegramBadRequest:
        pass


@router.callback_query(QuickMarkStates.choosing_date, F.data == "date_today")
async def date_today_qm(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    await callback.answer()
    data = await state.get_data()
    resolved: list[dict] = data["resolved"]
    lines = await _build_lines(session, resolved, datetime.now(UTC))
    await state.clear()
    summary = "✅ <b>Збережено:</b>\n\n" + "".join(lines) if lines else texts.CANCEL_ACTION
    try:
        await callback.message.edit_text(summary)
    except TelegramBadRequest:
        pass
    await callback.message.answer("Вибери наступну дію:", reply_markup=trainer_main_kb)


@router.callback_query(QuickMarkStates.choosing_date, F.data == "date_other")
async def date_other_qm(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(QuickMarkStates.enter_date)
    try:
        await callback.message.edit_text(texts.SBD_ASK_DATE)
    except TelegramBadRequest:
        pass


@router.callback_query(QuickMarkStates.confirming, F.data == "qm_cancel")
async def cancel_quick_mark(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    try:
        await callback.message.edit_text(texts.CANCEL_ACTION)
    except TelegramBadRequest:
        pass
    await callback.message.answer("Вибери дію:", reply_markup=trainer_main_kb)


async def _build_lines(
    session: AsyncSession,
    resolved: list[dict],
    occurred_at: datetime,
) -> list[str]:
    lines = []
    for item in resolved:
        if item["status"] is None:
            continue
        record, consumed, total, is_dup = await mark_attended(
            session,
            item["client_id"],
            _STATUS_MAP[item["status"]],
            occurred_at=occurred_at,
        )
        label = _STATUS_LABELS.get(item["status"], item["status"])
        if is_dup:
            lines.append(f"<b>{item['name']}</b> — {label} ⚠️ вже відмічено\n")
        elif consumed is not None:
            lines.append(f"<b>{item['name']}</b> — {label} ({consumed}/{total})\n")
        else:
            lines.append(f"<b>{item['name']}</b> — {label} ⚠️ немає пакета\n")
        if not is_dup:
            await audit_repo.write_entry(
                session,
                actor_type="trainer",
                actor_id=settings.trainer_telegram_id,
                action="mark_session",
                entity_type="session",
                entity_id=record.id,
                payload={
                    "client_name": item["name"],
                    "client_id": item["client_id"],
                    "status": item["status"],
                    "occurred_at": occurred_at.isoformat(),
                },
            )
            await session.commit()
    return lines
