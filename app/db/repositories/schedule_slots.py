from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.schedule_slot import ScheduleSlot


async def get_for_client(session: AsyncSession, client_id: int) -> list[ScheduleSlot]:
    result = await session.execute(
        select(ScheduleSlot)
        .where(ScheduleSlot.client_id == client_id, ScheduleSlot.is_active == True)
        .order_by(ScheduleSlot.weekday, ScheduleSlot.time_local)
    )
    return list(result.scalars().all())


async def get_all_active(session: AsyncSession) -> list[ScheduleSlot]:
    result = await session.execute(
        select(ScheduleSlot).where(ScheduleSlot.is_active == True)
    )
    return list(result.scalars().all())


async def create_slot(
    session: AsyncSession,
    client_id: int,
    weekday: int,
    time_local,
) -> ScheduleSlot:
    slot = ScheduleSlot(client_id=client_id, weekday=weekday, time_local=time_local)
    session.add(slot)
    await session.flush()
    return slot


async def deactivate_slot(session: AsyncSession, slot_id: int) -> None:
    slot = await session.get(ScheduleSlot, slot_id)
    if slot:
        slot.is_active = False
        await session.flush()
