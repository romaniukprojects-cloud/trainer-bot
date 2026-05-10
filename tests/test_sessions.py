from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.db.models.client import Client
from app.db.models.session_record import SessionStatus
from app.services.packages import register_payment
from app.services.sessions import mark_attended


async def _make_client(session, name="Тест") -> Client:
    client = Client(full_name=name, aliases=[])
    session.add(client)
    await session.flush()
    return client


# ─── mark_attended — basic ────────────────────────────────────────────────────

async def test_mark_attended_returns_record(db_session):
    client = await _make_client(db_session)
    await register_payment(db_session, client_id=client.id, price=Decimal("1000"))

    record, consumed, total, is_dup = await mark_attended(db_session, client.id)
    assert record.id is not None
    assert record.status == SessionStatus.attended
    assert consumed == 1
    assert total == 10
    assert is_dup is False


async def test_mark_attended_increments_consumed(db_session):
    client = await _make_client(db_session)
    await register_payment(db_session, client_id=client.id, price=Decimal("1000"))

    for i in range(1, 4):
        _, consumed, total, _ = await mark_attended(
            db_session, client.id, occurred_at=datetime(2025, 5, i, 10, 0, tzinfo=UTC)
        )
        assert consumed == i
        assert total == 10


# ─── idempotency ─────────────────────────────────────────────────────────────

async def test_mark_attended_duplicate_same_day(db_session):
    client = await _make_client(db_session)
    await register_payment(db_session, client_id=client.id, price=Decimal("1000"))

    t = datetime(2025, 5, 10, 10, 0, tzinfo=UTC)
    _, _, _, is_dup1 = await mark_attended(db_session, client.id, occurred_at=t)
    assert is_dup1 is False

    # Second mark on the same Kyiv calendar day — should be detected as duplicate.
    t2 = datetime(2025, 5, 10, 14, 0, tzinfo=UTC)
    _, c2, tot2, is_dup2 = await mark_attended(db_session, client.id, occurred_at=t2)
    assert is_dup2 is True
    assert c2 is None  # consumed not returned for duplicates


async def test_mark_attended_different_days_not_duplicate(db_session):
    client = await _make_client(db_session)
    await register_payment(db_session, client_id=client.id, price=Decimal("1000"))

    t1 = datetime(2025, 5, 10, 10, 0, tzinfo=UTC)
    t2 = datetime(2025, 5, 11, 10, 0, tzinfo=UTC)

    _, _, _, is_dup1 = await mark_attended(db_session, client.id, occurred_at=t1)
    _, _, _, is_dup2 = await mark_attended(db_session, client.id, occurred_at=t2)
    assert is_dup1 is False
    assert is_dup2 is False


# ─── session statuses ─────────────────────────────────────────────────────────

async def test_missed_no_notice_consumes_package(db_session):
    client = await _make_client(db_session)
    await register_payment(db_session, client_id=client.id, price=Decimal("1000"))

    _, consumed, total, is_dup = await mark_attended(
        db_session, client.id, status=SessionStatus.missed_no_notice
    )
    assert consumed == 1
    assert is_dup is False


async def test_cancelled_in_advance_does_not_consume_package(db_session):
    client = await _make_client(db_session)
    await register_payment(db_session, client_id=client.id, price=Decimal("1000"))

    _, consumed, total, _ = await mark_attended(
        db_session, client.id, status=SessionStatus.cancelled_in_advance
    )
    assert consumed is None  # no package consumed


async def test_cancelled_in_advance_no_idempotency_check(db_session):
    """Cancelled sessions don't trigger the same-day duplicate check."""
    client = await _make_client(db_session)
    await register_payment(db_session, client_id=client.id, price=Decimal("1000"))

    t = datetime(2025, 5, 10, 10, 0, tzinfo=UTC)
    _, _, _, is_dup1 = await mark_attended(
        db_session, client.id, status=SessionStatus.cancelled_in_advance, occurred_at=t
    )
    _, _, _, is_dup2 = await mark_attended(
        db_session, client.id, status=SessionStatus.cancelled_in_advance, occurred_at=t
    )
    # Duplicate guard only applies to countable statuses (attended, missed_no_notice).
    assert is_dup1 is False
    assert is_dup2 is False


# ─── no active package ───────────────────────────────────────────────────────

async def test_mark_attended_no_package(db_session):
    client = await _make_client(db_session)

    record, consumed, total, is_dup = await mark_attended(db_session, client.id)
    assert record.id is not None
    assert consumed is None
    assert total is None
    assert is_dup is False


# ─── missed_no_notice idempotency ────────────────────────────────────────────

async def test_missed_same_day_as_attended_is_duplicate(db_session):
    """If attended is already marked today, missed_no_notice on same day is duplicate too."""
    client = await _make_client(db_session)
    await register_payment(db_session, client_id=client.id, price=Decimal("1000"))

    t = datetime(2025, 5, 10, 10, 0, tzinfo=UTC)
    await mark_attended(db_session, client.id, status=SessionStatus.attended, occurred_at=t)

    _, _, _, is_dup = await mark_attended(
        db_session, client.id, status=SessionStatus.missed_no_notice, occurred_at=t
    )
    assert is_dup is True
