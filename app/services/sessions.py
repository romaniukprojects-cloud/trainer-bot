from datetime import UTC, datetime, timedelta, time
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models.package import PackageStatus
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
        await _schedule_payment_reminder(session, client_id)

    return record, consumed, total, False


async def _schedule_payment_reminder(session: AsyncSession, client_id: int) -> None:
    from app.db.repositories.clients import get_by_id
    from app.db.repositories.trainers import get_by_telegram_id as get_trainer
    from app.scheduler.jobs.payment_reminder import payment_reminder_job
    from app.scheduler.scheduler import scheduler

    client = await get_by_id(session, client_id)
    if client is None:
        return
    trainer = await get_trainer(session, settings.trainer_telegram_id)
    payment_details = trainer.payment_details if trainer else None

    run_date = datetime.now(UTC) + timedelta(hours=1)
    scheduler.add_job(
        payment_reminder_job,
        trigger="date",
        run_date=run_date,
        kwargs={"client_id": client_id, "payment_details": payment_details},
        id=f"pay_remind_{client_id}",
        replace_existing=True,
    )
