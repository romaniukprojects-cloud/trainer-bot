import enum
from datetime import UTC, datetime

from sqlalchemy import DateTime, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SessionStatus(enum.Enum):
    pending_confirmation = "pending_confirmation"
    attended = "attended"
    missed_no_notice = "missed_no_notice"         # counts against package
    cancelled_in_advance = "cancelled_in_advance"  # does NOT count
    cancelled_by_trainer = "cancelled_by_trainer"


class SessionSource(enum.Enum):
    manual = "manual"
    auto_schedule = "auto_schedule"


class SessionRecord(Base):
    __tablename__ = "sessions"
    # Partial unique index created via raw SQL in the initial migration:
    # CREATE UNIQUE INDEX ix_no_duplicate_auto_sessions
    #   ON sessions (schedule_slot_id, date(scheduled_at))
    #   WHERE schedule_slot_id IS NOT NULL

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False)
    package_id: Mapped[int | None] = mapped_column(ForeignKey("packages.id"), nullable=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[SessionStatus] = mapped_column(Enum(SessionStatus), nullable=False)
    source: Mapped[SessionSource] = mapped_column(
        Enum(SessionSource), nullable=False, default=SessionSource.manual
    )
    schedule_slot_id: Mapped[int | None] = mapped_column(
        ForeignKey("schedule_slots.id"), nullable=True
    )
    note: Mapped[str | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
