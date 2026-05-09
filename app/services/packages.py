from datetime import UTC, datetime
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.package import Package
from app.db.repositories import packages as repo


async def register_payment(
    session: AsyncSession,
    client_id: int,
    price: Decimal,
    purchased_at: datetime | None = None,
) -> Package:
    now = purchased_at or datetime.now(UTC)
    expires_at = now + relativedelta(months=1)
    package = await repo.create(
        session,
        client_id=client_id,
        purchased_at=now,
        expires_at=expires_at,
        price=price,
    )
    await session.commit()
    return package


async def find_active_for_consumption(session: AsyncSession, client_id: int) -> Package | None:
    """Returns the active package expiring soonest that still has sessions (FIFO)."""
    packages = await repo.get_active_for_client(session, client_id)
    for pkg in packages:
        count = await repo.get_consumed_count(session, pkg.id)
        if count < pkg.total_sessions:
            return pkg
    return None


async def get_active_packages(session: AsyncSession, client_id: int) -> list[Package]:
    return await repo.get_active_for_client(session, client_id)
