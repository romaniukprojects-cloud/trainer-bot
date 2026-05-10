from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.client import Client
from app.db.models.session_record import SessionRecord, SessionStatus


async def find_countable_on_date(
    session: AsyncSession,
    client_id: int,
    day_start: datetime,
    day_end: datetime,
) -> SessionRecord | None:
    result = await session.execute(
        select(SessionRecord).where(
            SessionRecord.client_id == client_id,
            SessionRecord.status.in_([SessionStatus.attended, SessionStatus.missed_no_notice]),
            SessionRecord.occurred_at >= day_start,
            SessionRecord.occurred_at < day_end,
        )
    )
    return result.scalars().first()


async def create(session: AsyncSession, **kwargs) -> SessionRecord:
    record = SessionRecord(**kwargs)
    session.add(record)
    await session.flush()
    return record


async def get_all_on_date(
    session: AsyncSession,
    day_start: datetime,
    day_end: datetime,
) -> list[tuple[SessionRecord, str]]:
    result = await session.execute(
        select(SessionRecord, Client.full_name)
        .join(Client, SessionRecord.client_id == Client.id)
        .where(
            SessionRecord.occurred_at >= day_start,
            SessionRecord.occurred_at < day_end,
            SessionRecord.status.in_([
                SessionStatus.attended,
                SessionStatus.missed_no_notice,
                SessionStatus.cancelled_in_advance,
            ]),
        )
        .order_by(SessionRecord.occurred_at.asc(), Client.full_name.asc())
    )
    return list(result.all())


async def get_recent_for_client(
    session: AsyncSession, client_id: int, limit: int = 10
) -> list[SessionRecord]:
    result = await session.execute(
        select(SessionRecord)
        .where(SessionRecord.client_id == client_id)
        .order_by(
            SessionRecord.occurred_at.desc().nullslast(),
            SessionRecord.created_at.desc(),
        )
        .limit(limit)
    )
    return list(result.scalars().all())
