from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from app.config import settings


def to_kyiv(dt: datetime) -> datetime:
    return dt.astimezone(ZoneInfo(settings.timezone))


def to_utc(dt: datetime) -> datetime:
    return dt.astimezone(UTC)


def now_kyiv() -> datetime:
    return datetime.now(ZoneInfo(settings.timezone))


def now_utc() -> datetime:
    return datetime.now(UTC)
