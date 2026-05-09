import logging
from datetime import UTC, datetime

from sqlalchemy import select

from app.db.base import AsyncSessionLocal
from app.db.models.package import Package, PackageStatus
from app.db.repositories.packages import get_consumed_count

logger = logging.getLogger(__name__)


async def expire_packages_job() -> None:
    async with AsyncSessionLocal() as session:
        now = datetime.now(UTC)
        result = await session.execute(
            select(Package).where(Package.status == PackageStatus.active)
        )
        packages = list(result.scalars().all())

        expired = exhausted = 0
        for pkg in packages:
            consumed = await get_consumed_count(session, pkg.id)
            if consumed >= pkg.total_sessions:
                pkg.status = PackageStatus.exhausted
                exhausted += 1
            elif pkg.expires_at <= now:
                pkg.status = PackageStatus.expired
                expired += 1

        await session.commit()
        logger.info("expire_packages: expired=%d exhausted=%d", expired, exhausted)
