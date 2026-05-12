from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.package import Package, PackageStatus
from app.db.models.session_record import SessionRecord, SessionStatus


async def get_active_for_client(session: AsyncSession, client_id: int) -> list[Package]:
    result = await session.execute(
        select(Package)
        .where(Package.client_id == client_id, Package.status == PackageStatus.active)
        .order_by(Package.expires_at.asc())
    )
    return list(result.scalars().all())


async def get_consumed_count(session: AsyncSession, package_id: int) -> int:
    result = await session.execute(
        select(func.count()).where(
            SessionRecord.package_id == package_id,
            SessionRecord.status.in_([SessionStatus.attended, SessionStatus.missed_no_notice]),
        )
    )
    return result.scalar_one()


async def create(session: AsyncSession, **kwargs) -> Package:
    package = Package(**kwargs)
    session.add(package)
    await session.flush()
    return package


async def get_income_for_period(
    session: AsyncSession,
    period_start: datetime,
    period_end: datetime,
) -> tuple[Decimal, int]:
    """Returns (total_income, package_count) for packages purchased in the period."""
    result = await session.execute(
        select(func.sum(Package.price), func.count(Package.id))
        .where(
            Package.purchased_at >= period_start,
            Package.purchased_at < period_end,
            Package.status != PackageStatus.cancelled,
        )
    )
    row = result.one()
    return (row[0] or Decimal(0), row[1] or 0)
