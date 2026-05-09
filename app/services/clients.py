from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.client import Client
from app.db.repositories import clients as repo
from app.utils.codes import generate_link_code


async def add_client(
    session: AsyncSession,
    full_name: str,
    phone: str | None = None,
    aliases: list[str] | None = None,
) -> Client:
    client = await repo.create(
        session,
        full_name=full_name,
        phone=phone,
        aliases=aliases or [],
    )
    await session.commit()
    return client


async def create_link_code(session: AsyncSession, client: Client) -> str:
    code = generate_link_code()
    client.link_code = code
    client.link_code_expires_at = datetime.now(UTC) + timedelta(hours=24)
    await session.commit()
    return code


async def link_telegram(
    session: AsyncSession,
    code: str,
    tg_user_id: int,
    tg_username: str | None,
) -> Client | None:
    client = await repo.get_by_link_code(session, code)
    if client is None:
        return None
    if client.link_code_expires_at and client.link_code_expires_at < datetime.now(UTC):
        return None
    client.telegram_user_id = tg_user_id
    client.telegram_username = tg_username
    client.link_code = None
    client.link_code_expires_at = None
    await session.commit()
    return client


async def get_active_clients(session: AsyncSession) -> list[Client]:
    return await repo.get_active_all(session)
