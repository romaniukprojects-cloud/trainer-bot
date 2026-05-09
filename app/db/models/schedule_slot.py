from sqlalchemy import Date, ForeignKey, SmallInteger, Time
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from datetime import date, time


class ScheduleSlot(Base):
    __tablename__ = "schedule_slots"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False)
    # 0 = Monday … 6 = Sunday
    weekday: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    time_local: Mapped[time] = mapped_column(Time, nullable=False)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
