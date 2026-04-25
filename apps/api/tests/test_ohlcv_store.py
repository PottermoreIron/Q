"""
Bitemporal OHLCV store tests.

Requires real PostgreSQL (testcontainers) — skipped without Docker.
"""

from datetime import datetime, timezone

import pytest

from schemas.data import OHLCVBar
from services.data.store import read_bars, write_bars

BASE_MS = 1_672_531_200_000  # 2023-01-01 00:00 UTC


def _bar(i: int, close: float = 100.0) -> OHLCVBar:
    return OHLCVBar(
        timestamp=BASE_MS + i * 86_400_000,
        open=99.0, high=101.0, low=98.0,
        close=close, volume=1000.0,
    )


T0 = datetime(2023, 1, 1, tzinfo=timezone.utc)
T1 = datetime(2023, 6, 1, tzinfo=timezone.utc)
T2 = datetime(2024, 1, 1, tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_write_and_read_basic(db):
    bars = [_bar(i) for i in range(5)]
    await write_bars(db, "AAPL", "yahoo", "1d", bars, fetched_at=T1)

    result = await read_bars(db, "AAPL", "yahoo", "1d",
                             BASE_MS, BASE_MS + 10 * 86_400_000, as_of=T2)
    assert len(result) == 5
    assert result[0].timestamp == BASE_MS
    assert result[0].close == pytest.approx(100.0)


@pytest.mark.asyncio
async def test_write_identical_is_noop(db):
    bars = [_bar(0)]
    await write_bars(db, "MSFT", "yahoo", "1d", bars, fetched_at=T0)
    await write_bars(db, "MSFT", "yahoo", "1d", bars, fetched_at=T1)

    from sqlalchemy import select
    from models.ohlcv_bar import OHLCVBarRow
    stmt = select(OHLCVBarRow).where(
        OHLCVBarRow.symbol == "MSFT",
        OHLCVBarRow.ts == BASE_MS,
    )
    rows = (await db.execute(stmt)).scalars().all()
    # Only one row — the no-op did not insert a second
    assert len(rows) == 1
    assert rows[0].effective_to is None


@pytest.mark.asyncio
async def test_upstream_correction_closes_old_row(db):
    original = _bar(0, close=100.0)
    corrected = _bar(0, close=101.5)

    await write_bars(db, "GOOG", "yahoo", "1d", [original], fetched_at=T0)
    await write_bars(db, "GOOG", "yahoo", "1d", [corrected], fetched_at=T1)

    from sqlalchemy import select
    from models.ohlcv_bar import OHLCVBarRow
    stmt = select(OHLCVBarRow).where(
        OHLCVBarRow.symbol == "GOOG",
        OHLCVBarRow.ts == BASE_MS,
    ).order_by(OHLCVBarRow.effective_from)
    rows = (await db.execute(stmt)).scalars().all()

    assert len(rows) == 2
    assert rows[0].close == pytest.approx(100.0)
    assert rows[0].effective_to is not None  # closed
    assert rows[1].close == pytest.approx(101.5)
    assert rows[1].effective_to is None      # open


@pytest.mark.asyncio
async def test_point_in_time_replay(db):
    original  = _bar(0, close=100.0)
    corrected = _bar(0, close=105.0)

    await write_bars(db, "AMZN", "yahoo", "1d", [original], fetched_at=T0)
    await write_bars(db, "AMZN", "yahoo", "1d", [corrected], fetched_at=T1)

    # Query as_of T0 → should see original value
    at_t0 = await read_bars(db, "AMZN", "yahoo", "1d",
                            BASE_MS, BASE_MS + 86_400_000, as_of=T0)
    assert len(at_t0) == 1
    assert at_t0[0].close == pytest.approx(100.0)

    # Query as_of T2 → should see corrected value
    at_t2 = await read_bars(db, "AMZN", "yahoo", "1d",
                            BASE_MS, BASE_MS + 86_400_000, as_of=T2)
    assert len(at_t2) == 1
    assert at_t2[0].close == pytest.approx(105.0)


@pytest.mark.asyncio
async def test_read_empty_range(db):
    result = await read_bars(db, "TSLA", "yahoo", "1d", BASE_MS, BASE_MS, as_of=T2)
    assert result == []
