"""
DataProvider Protocol and shared utilities (cache, DataFrame → OHLCVBar).

Every provider implements this Protocol. Nothing provider-specific leaks
into the rest of the codebase — that is the entire point of this layer.
"""
from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Optional, Protocol, runtime_checkable

if TYPE_CHECKING:
    import pandas as pd

from schemas.data import OHLCVBar, SymbolSearchResult

_CACHE_TTL = 3600  # 1 hour


@runtime_checkable
class DataProvider(Protocol):
    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        start_date: str,
        end_date: str,
    ) -> list[OHLCVBar]: ...

    async def search(self, query: str) -> list[SymbolSearchResult]: ...


# ── Cache helpers ─────────────────────────────────────────────────────────────

def make_cache_key(source: str, symbol: str, timeframe: str, start: str, end: str) -> str:
    raw = f"{source}:{symbol}:{timeframe}:{start}:{end}"
    return "ohlcv:" + hashlib.md5(raw.encode()).hexdigest()


async def cache_get(key: str) -> Optional[list[OHLCVBar]]:
    try:
        import redis.asyncio as aioredis
        from config import settings
        r = aioredis.from_url(settings.redis_url, decode_responses=True)
        data = await r.get(key)
        await r.aclose()
        if data:
            return [OHLCVBar(**b) for b in json.loads(data)]
    except Exception:
        pass
    return None


async def cache_set(key: str, bars: list[OHLCVBar]) -> None:
    try:
        import redis.asyncio as aioredis
        from config import settings
        r = aioredis.from_url(settings.redis_url, decode_responses=True)
        await r.setex(key, _CACHE_TTL, json.dumps([b.model_dump() for b in bars]))
        await r.aclose()
    except Exception:
        pass


# ── DataFrame normaliser ──────────────────────────────────────────────────────

def df_to_bars(df: "pd.DataFrame") -> list[OHLCVBar]:
    """
    Normalise any OHLCV DataFrame to a list of OHLCVBar.

    Handles:
    - Timestamp in index or as a column named date/datetime/timestamp/time
    - Timezone-aware or naive datetimes (always stored as UTC ms)
    - Columns named open/high/low/close/volume (case-insensitive)
    """
    import pandas as pd

    df = df.copy()
    df.columns = [str(c).lower() for c in df.columns]

    # Promote index to column if it carries the timestamp
    if df.index.name and str(df.index.name).lower() in ("date", "datetime", "timestamp"):
        df = df.reset_index()
        ts_col = str(df.columns[0]).lower()
        df.rename(columns={df.columns[0]: ts_col}, inplace=True)
    else:
        ts_col = next(
            (c for c in df.columns if c in ("date", "datetime", "timestamp", "time")),
            None,
        )
        if ts_col is None:
            raise ValueError("No timestamp column found in DataFrame")

    # Parse to UTC-aware, then to int64 ms
    parsed = pd.to_datetime(df[ts_col], utc=True)
    df["ts_ms"] = parsed.astype("int64") // 1_000_000

    bars: list[OHLCVBar] = []
    for row in df.itertuples(index=False):
        bars.append(OHLCVBar(
            timestamp=int(row.ts_ms),
            open=float(row.open),
            high=float(row.high),
            low=float(row.low),
            close=float(row.close),
            volume=float(row.volume),
        ))
    return bars
