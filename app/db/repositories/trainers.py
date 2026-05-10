from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.trainer import Trainer


async def get_by_telegram_id(session: AsyncSession, telegram_user_id: int) -> Trainer | None:
    result = await session.execute(
        select(Trainer).where(Trainer.telegram_user_id == telegram_user_id)
    )
    return result.scalar_one_or_none()


async def get_or_create(session: AsyncSession, telegram_user_id: int, full_name: str) -> Trainer:
    trainer = await get_by_telegram_id(session, telegram_user_id)
    if trainer is None:
        trainer = Trainer(telegram_user_id=telegram_user_id, full_name=full_name)
        session.add(trainer)
        await session.flush()
    return trainer


async def update_payment_details(
    session: AsyncSession, telegram_user_id: int, payment_details: str
) -> None:
    trainer = await get_by_telegram_id(session, telegram_user_id)
    if trainer:
        trainer.payment_details = payment_details
