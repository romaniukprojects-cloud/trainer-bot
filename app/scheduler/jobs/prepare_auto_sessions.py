import logging
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from app.config import settings
from app.db.base import AsyncSessionLocal
from app.db.models.session_record import SessionRecord, SessionSource, SessionStatus
from app.db.repositories.schedule_slots import get_all_active
from app.db.repositories.sessions import find_auto_session_for_slot_date

logger = logging.getLogger(__name__)


async def prepare_auto_sessions_job() -> None:
    kyiv = ZoneInfo(settings.timezone)
    today_kyiv = datetime.now(kyiv).date()

    async with AsyncSessionLocal() as session:
        slots = await get_all_active(session)
        created = 0

        for days_ahead in range(1, 8):
            target_date = today_kyiv + timedelta(days=days_ahead)
            target_weekday = target_date.weekday()

            for slot in slots:
                if slot.weekday != target_weekday:
                    continue
                if slot.valid_from and target_date < slot.valid_from:
                    continue
                if slot.valid_until and target_date > slot.valid_until:
                    continue

                existing = await find_auto_session_for_slot_date(
                    session, slot.id, target_date, settings.timezone
                )
                if existing:
                    continue

                scheduled_at = datetime.combine(
                    target_date, slot.time_local, tzinfo=kyiv
                ).astimezone(UTC)

                rec = SessionRecord(
                    client_id=slot.client_id,
                    schedule_slot_id=slot.id,
                    scheduled_at=scheduled_at,
                    status=SessionStatus.pending_confirmation,
                    source=SessionSource.auto_schedule,
                )
                session.add(rec)
                created += 1

        await session.commit()
        logger.info("prepare_auto_sessions: created=%d", created)
