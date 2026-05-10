import logging
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from app.config import settings
from app.db.base import AsyncSessionLocal
from app.db.models.package import PackageStatus
from app.db.models.session_record import SessionStatus
from app.db.repositories import packages as pkg_repo
from app.db.repositories.sessions import find_countable_on_date, find_overdue_pending
from app.services.packages import find_active_for_consumption

logger = logging.getLogger(__name__)


async def auto_finalize_job() -> None:
    now = datetime.now(UTC)
    cutoff = now - timedelta(hours=4)
    kyiv = ZoneInfo(settings.timezone)

    async with AsyncSessionLocal() as session:
        sessions = await find_overdue_pending(session, cutoff)
        finalized = skipped = 0

        for rec in sessions:
            # If the trainer already recorded this session manually, cancel the auto one
            scheduled_kyiv = rec.scheduled_at.astimezone(kyiv)
            target_date = scheduled_kyiv.date()
            day_start = datetime.combine(
                target_date, datetime.min.time(), tzinfo=kyiv
            ).astimezone(UTC)
            day_end = datetime.combine(
                target_date + timedelta(days=1), datetime.min.time(), tzinfo=kyiv
            ).astimezone(UTC)

            existing = await find_countable_on_date(session, rec.client_id, day_start, day_end)
            if existing and existing.id != rec.id:
                rec.status = SessionStatus.cancelled_by_trainer
                skipped += 1
                continue

            rec.status = SessionStatus.attended
            rec.occurred_at = now

            package = await find_active_for_consumption(session, rec.client_id)
            if package:
                rec.package_id = package.id
                await session.flush()
                consumed = await pkg_repo.get_consumed_count(session, package.id)
                if consumed >= package.total_sessions:
                    package.status = PackageStatus.exhausted

            finalized += 1

        await session.commit()
        logger.info("auto_finalize: finalized=%d skipped=%d", finalized, skipped)
