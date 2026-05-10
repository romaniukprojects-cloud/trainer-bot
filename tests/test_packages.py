from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.db.models.client import Client
from app.db.models.package import Package, PackageStatus
from app.db.repositories.packages import get_consumed_count
from app.services.packages import find_active_for_consumption, register_payment


async def _make_client(session, name="Тест Клієнт") -> Client:
    client = Client(full_name=name, aliases=[])
    session.add(client)
    await session.flush()
    return client


# ─── register_payment ────────────────────────────────────────────────────────

async def test_register_payment_creates_package(db_session):
    client = await _make_client(db_session)
    pkg = await register_payment(db_session, client_id=client.id, price=Decimal("1500"))
    assert pkg.id is not None
    assert pkg.client_id == client.id
    assert pkg.status == PackageStatus.active
    assert pkg.total_sessions == 10
    assert pkg.price == Decimal("1500")


async def test_register_payment_expires_one_month(db_session):
    client = await _make_client(db_session)
    purchased = datetime(2025, 1, 31, tzinfo=UTC)
    pkg = await register_payment(db_session, client_id=client.id, price=Decimal("1000"), purchased_at=purchased)
    # 31 Jan + 1 month = 28 Feb (relativedelta handles month-end correctly)
    assert pkg.expires_at.month == 2
    assert pkg.expires_at.day == 28
    assert pkg.expires_at.year == 2025


async def test_register_payment_backdate(db_session):
    client = await _make_client(db_session)
    purchased = datetime(2025, 3, 15, tzinfo=UTC)
    pkg = await register_payment(db_session, client_id=client.id, price=Decimal("1000"), purchased_at=purchased)
    assert pkg.purchased_at == purchased
    assert pkg.expires_at.month == 4
    assert pkg.expires_at.day == 15


# ─── find_active_for_consumption (FIFO) ──────────────────────────────────────

async def test_find_active_returns_none_when_no_packages(db_session):
    client = await _make_client(db_session)
    result = await find_active_for_consumption(db_session, client.id)
    assert result is None


async def test_find_active_returns_package(db_session):
    client = await _make_client(db_session)
    pkg = await register_payment(db_session, client_id=client.id, price=Decimal("1000"))
    result = await find_active_for_consumption(db_session, client.id)
    assert result is not None
    assert result.id == pkg.id


async def test_find_active_fifo_picks_earliest_expiring(db_session):
    """With two active packages, the one expiring sooner should be picked."""
    client = await _make_client(db_session)
    early = datetime(2025, 1, 1, tzinfo=UTC)
    late = datetime(2025, 3, 1, tzinfo=UTC)

    pkg_late = await register_payment(db_session, client_id=client.id, price=Decimal("1000"), purchased_at=late)
    pkg_early = await register_payment(db_session, client_id=client.id, price=Decimal("1000"), purchased_at=early)

    result = await find_active_for_consumption(db_session, client.id)
    assert result.id == pkg_early.id


async def test_find_active_skips_exhausted_package(db_session):
    """A package with 10/10 sessions consumed must be skipped; next one returned."""
    from app.db.models.session_record import SessionRecord, SessionSource, SessionStatus

    client = await _make_client(db_session)
    early = datetime(2025, 1, 1, tzinfo=UTC)
    late = datetime(2025, 3, 1, tzinfo=UTC)

    pkg_full = await register_payment(db_session, client_id=client.id, price=Decimal("1000"), purchased_at=early)
    pkg_free = await register_payment(db_session, client_id=client.id, price=Decimal("1000"), purchased_at=late)

    # Fill up pkg_full with 10 sessions.
    for _ in range(10):
        rec = SessionRecord(
            client_id=client.id,
            package_id=pkg_full.id,
            occurred_at=datetime.now(UTC),
            status=SessionStatus.attended,
            source=SessionSource.manual,
        )
        db_session.add(rec)
    await db_session.flush()

    result = await find_active_for_consumption(db_session, client.id)
    assert result is not None
    assert result.id == pkg_free.id


async def test_get_consumed_count(db_session):
    from app.db.models.session_record import SessionRecord, SessionSource, SessionStatus

    client = await _make_client(db_session)
    pkg = await register_payment(db_session, client_id=client.id, price=Decimal("1000"))

    for _ in range(3):
        rec = SessionRecord(
            client_id=client.id,
            package_id=pkg.id,
            occurred_at=datetime.now(UTC),
            status=SessionStatus.attended,
            source=SessionSource.manual,
        )
        db_session.add(rec)
    await db_session.flush()

    count = await get_consumed_count(db_session, pkg.id)
    assert count == 3


async def test_cancelled_in_advance_not_counted(db_session):
    from app.db.models.session_record import SessionRecord, SessionSource, SessionStatus

    client = await _make_client(db_session)
    pkg = await register_payment(db_session, client_id=client.id, price=Decimal("1000"))

    rec = SessionRecord(
        client_id=client.id,
        package_id=pkg.id,
        occurred_at=datetime.now(UTC),
        status=SessionStatus.cancelled_in_advance,
        source=SessionSource.manual,
    )
    db_session.add(rec)
    await db_session.flush()

    count = await get_consumed_count(db_session, pkg.id)
    assert count == 0
