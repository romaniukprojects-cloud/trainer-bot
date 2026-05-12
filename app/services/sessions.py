from datetime import UTC, datetime, timedelta, time
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models.package import Package, PackageStatus
from app.db.models.session_record import SessionRecord, SessionSource, SessionStatus
from app.db.repositories import packages as pkg_repo
from app.db.repositories import sessions as repo
from app.services.packages import find_active_for_consumption


async def mark_attended(
    session: AsyncSession,
    client_id: int,
    status: SessionStatus = SessionStatus.attended,
    occurred_at: datetime | None = None,
) -> tuple[SessionRecord, int | None, int | None, bool]:
    """Mark a session. Returns (record, consumed, total, is_duplicate).
    is_duplicate=True when a countable session already exists for this client today."""
    occurred_at = occurred_at or datetime.now(UTC)

    if status in (SessionStatus.attended, SessionStatus.missed_no_notice):
        kyiv = ZoneInfo(settings.timezone)
        kyiv_date = occurred_at.astimezone(kyiv).date()
        day_start = datetime.combine(kyiv_date, time.min, tzinfo=kyiv).astimezone(UTC)
        day_end = datetime.combine(kyiv_date + timedelta(days=1), time.min, tzinfo=kyiv).astimezone(UTC)
        existing = await repo.find_countable_on_date(session, client_id, day_start, day_end)
        if existing:
            return existing, None, None, True

    package = None
    if status in (SessionStatus.attended, SessionStatus.missed_no_notice):
        package = await find_active_for_consumption(session, client_id)

    record = await repo.create(
        session,
        client_id=client_id,
        package_id=package.id if package else None,
        occurred_at=occurred_at,
        status=status,
        source=SessionSource.manual,
    )

    consumed = None
    total = None
    should_remind = False
    if package:
        consumed = await pkg_repo.get_consumed_count(session, package.id)
        total = package.total_sessions
        if consumed >= total:
            package.status = PackageStatus.exhausted
        elif consumed == 9 and package.last_payment_reminder_at is None:
            package.last_payment_reminder_at = datetime.now(UTC)
            should_remind = True

    await session.commit()

    if should_remind:
        await _schedule_payment_reminder(session, client_id, package.expires_at)

    return record, consumed, total, False


async def cancel_training_day(
    session: AsyncSession,
    day_start: datetime,
    day_end: datetime,
) -> list[tuple[str, str]]:
    """Cancel all attended/missed sessions in the given UTC window.

    Returns list of (client_name, old_status_label) for the summary.
    Reverts exhausted packages back to active if cancellation frees up a slot.
    """
    from app.db.repositories.sessions import get_countable_for_date

    rows = await get_countable_for_date(session, day_start, day_end)
    if not rows:
        return []

    _STATUS_LABELS = {
        SessionStatus.attended: "✅ прийшов",
        SessionStatus.missed_no_notice: "🚫 пропуск",
    }

    affected_package_ids: set[int] = set()
    summary: list[tuple[str, str]] = []

    for record, client_name in rows:
        label = _STATUS_LABELS.get(record.status, record.status.value)
        summary.append((client_name, label))
        if record.package_id:
            affected_package_ids.add(record.package_id)
        record.status = SessionStatus.cancelled_by_trainer

    await session.flush()

    for pkg_id in affected_package_ids:
        pkg = await session.get(Package, pkg_id)
        if pkg and pkg.status == PackageStatus.exhausted:
            consumed = await pkg_repo.get_consumed_count(session, pkg_id)
            if consumed < pkg.total_sessions:
                pkg.status = PackageStatus.active

    await session.commit()
    return summary


async def _schedule_payment_reminder(
    session: AsyncSession, client_id: int, expires_at: datetime | None
) -> None:
    from app.db.repositories.clients import get_by_id
    from app.db.repositories.trainers import get_by_telegram_id as get_trainer
    from app.scheduler.jobs.payment_reminder import payment_reminder_job
    from app.scheduler.scheduler import scheduler
    from app.utils.tz import to_kyiv

    client = await get_by_id(session, client_id)
    if client is None:
        return
    trainer = await get_trainer(session, settings.trainer_telegram_id)
    payment_details = trainer.payment_details if trainer else None

    expires_str = to_kyiv(expires_at).strftime("%d.%m.%Y") if expires_at else None

    run_date = datetime.now(UTC) + timedelta(hours=1)
    scheduler.add_job(
        payment_reminder_job,
        trigger="date",
        run_date=run_date,
        kwargs={
            "client_id": client_id,
            "payment_details": payment_details,
            "expires_at_str": expires_str,
        },
        id=f"pay_remind_{client_id}",
        replace_existing=True,
    )
