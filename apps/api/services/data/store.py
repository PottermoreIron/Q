"""
Bitemporal OHLCV repository.

read_bars(symbol, source, timeframe, start_ms, end_ms, as_of)
    → list[OHLCVBar] from the store as-of a given timestamp.
    Returns [] when the range is not covered — callers must then fetch
    upstream and call write_bars().

write_bars(symbol, source, timeframe, bars, fetched_at)
    → append-only write:
    - Identical bar (same ts, same OHLCV) → no-op.
    - Changed bar → close the open row (effective_to = fetched_at), insert new row.
    - New bar → insert new row.

Redis remains a hot-path accelerator on top of this store (keyed on the
query hash including as_of).  It is never the source of truth.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Sequence

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.ohlcv_bar import OHLCVBarRow
from schemas.data import OHLCVBar


async def read_bars(
    db: AsyncSession,
    symbol: str,
    source: str,
    timeframe: str,
    start_ms: int,
    end_ms: int,
    as_of: datetime,
) -> list[OHLCVBar]:
    """
    Return bars where effective_from <= as_of < (effective_to OR ∞),
    ordered by ts ascending, within [start_ms, end_ms].
    """
    stmt = (
        select(OHLCVBarRow)
        .where(
            OHLCVBarRow.symbol    == symbol,
            OHLCVBarRow.source    == source,
            OHLCVBarRow.timeframe == timeframe,
            OHLCVBarRow.ts >= start_ms,
            OHLCVBarRow.ts <= end_ms,
            OHLCVBarRow.effective_from <= as_of,
            or_(
                OHLCVBarRow.effective_to.is_(None),
                OHLCVBarRow.effective_to > as_of,
            ),
        )
        .order_by(OHLCVBarRow.ts)
    )
    result = await db.execute(stmt)
    rows: Sequence[OHLCVBarRow] = result.scalars().all()
    return [
        OHLCVBar(
            timestamp=row.ts,
            open=row.open,
            high=row.high,
            low=row.low,
            close=row.close,
            volume=row.volume,
        )
        for row in rows
    ]


async def write_bars(
    db: AsyncSession,
    symbol: str,
    source: str,
    timeframe: str,
    bars: list[OHLCVBar],
    fetched_at: Optional[datetime] = None,
) -> None:
    """
    Append-only write:
    - Same (symbol, source, timeframe, ts) with identical OHLCV → no-op.
    - Different OHLCV → close open row, insert corrected row.
    - New ts → insert.
    """
    if not bars:
        return

    now = fetched_at or datetime.now(timezone.utc)

    # Load existing open rows for these timestamps in one query
    ts_list = [b.timestamp for b in bars]
    stmt = select(OHLCVBarRow).where(
        OHLCVBarRow.symbol    == symbol,
        OHLCVBarRow.source    == source,
        OHLCVBarRow.timeframe == timeframe,
        OHLCVBarRow.ts.in_(ts_list),
        OHLCVBarRow.effective_to.is_(None),
    )
    result   = await db.execute(stmt)
    existing = {row.ts: row for row in result.scalars().all()}

    for bar in bars:
        row = existing.get(bar.timestamp)

        if row is None:
            # New bar
            db.add(OHLCVBarRow(
                symbol=symbol, source=source, timeframe=timeframe,
                ts=bar.timestamp,
                open=bar.open, high=bar.high, low=bar.low,
                close=bar.close, volume=bar.volume,
                fetched_at=now, effective_from=now, effective_to=None,
            ))
        elif _values_equal(row, bar):
            # Identical — no-op
            pass
        else:
            # Upstream correction: close the old row, insert new
            row.effective_to = now
            db.add(OHLCVBarRow(
                symbol=symbol, source=source, timeframe=timeframe,
                ts=bar.timestamp,
                open=bar.open, high=bar.high, low=bar.low,
                close=bar.close, volume=bar.volume,
                fetched_at=now, effective_from=now, effective_to=None,
            ))

    await db.commit()


def _values_equal(row: OHLCVBarRow, bar: OHLCVBar) -> bool:
    eps = 1e-9
    return (
        abs(row.open   - bar.open)   < eps and
        abs(row.high   - bar.high)   < eps and
        abs(row.low    - bar.low)    < eps and
        abs(row.close  - bar.close)  < eps and
        abs(row.volume - bar.volume) < eps
    )
