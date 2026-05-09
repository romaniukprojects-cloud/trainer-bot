from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.client import Client


async def get_by_id(session: AsyncSession, client_id: int) -> Client | None:
    result = await session.execute(select(Client).where(Client.id == client_id))
    return result.scalar_one_or_none()


async def get_by_telegram_id(session: AsyncSession, tg_id: int) -> Client | None:
    result = await session.execute(select(Client).where(Client.telegram_user_id == tg_id))
    return result.scalar_one_or_none()


async def get_by_link_code(session: AsyncSession, code: str) -> Client | None:
    result = await session.execute(select(Client).where(Client.link_code == code))
    return result.scalar_one_or_none()


async def get_active_all(session: AsyncSession) -> list[Client]:
    result = await session.execute(
        select(Client).where(Client.is_active == True).order_by(Client.full_name)
    )
    return list(result.scalars().all())


async def create(session: AsyncSession, **kwargs) -> Client:
    client = Client(**kwargs)
    session.add(client)
    await session.flush()
    return client
