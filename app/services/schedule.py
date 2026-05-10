from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.package import PackageStatus
from app.db.models.session_record import SessionRecord, SessionStatus
from app.db.repositories import packages as pkg_repo
from app.services.packages import find_active_for_consumption


async def confirm_session(
    session: AsyncSession,
    session_id: int,
    status: SessionStatus,
) -> tuple[SessionRecord | None, int | None, int | None]:
    """Finalize a pending_confirmation session. Returns (record, consumed, total).
    If record not found or already finalized, returns (record, None, None)."""
    rec = await session.get(SessionRecord, session_id)
    if rec is None or rec.status != SessionStatus.pending_confirmation:
        return rec, None, None

    rec.status = status
    rec.occurred_at = datetime.now(UTC)

    consumed = None
    total = None

    if status in (SessionStatus.attended, SessionStatus.missed_no_notice):
        package = await find_active_for_consumption(session, rec.client_id)
        if package:
            rec.package_id = package.id
            await session.flush()
            consumed = await pkg_repo.get_consumed_count(session, package.id)
            total = package.total_sessions
            if consumed >= total:
                package.status = PackageStatus.exhausted
            elif consumed == 9 and package.last_payment_reminder_at is None:
                package.last_payment_reminder_at = datetime.now(UTC)
                await session.flush()
                await _schedule_payment_reminder(session, rec.client_id)

    await session.commit()
    return rec, consumed, total


async def _schedule_payment_reminder(session: AsyncSession, client_id: int) -> None:
    from app.config import settings
    from app.db.repositories.clients import get_by_id
    from app.db.repositories.trainers import get_by_telegram_id
    from app.scheduler.jobs.payment_reminder import payment_reminder_job
    from app.scheduler.scheduler import scheduler

    client = await get_by_id(session, client_id)
    if client is None:
        return
    trainer = await get_by_telegram_id(session, settings.trainer_telegram_id)
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
