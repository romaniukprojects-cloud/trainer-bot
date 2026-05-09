from datetime import datetime

from app.utils.tz import to_kyiv, now_kyiv

_WEEKDAYS_UK = ("пн", "вт", "ср", "чт", "пт", "сб", "нд")


def fmt_date(dt: datetime) -> str:
    return to_kyiv(dt).strftime("%d.%m.%Y")


def fmt_date_weekday(dt: datetime) -> str:
    local = to_kyiv(dt)
    wd = _WEEKDAYS_UK[local.weekday()]
    return local.strftime(f"%d.%m.%Y ({wd})")


def days_until(dt: datetime) -> int:
    return (to_kyiv(dt).date() - now_kyiv().date()).days
