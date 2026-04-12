"""
Data ingestion connectors.

Free:
  yfinance  → stocks / ETFs / indices (Yahoo Finance)
  ccxt      → crypto (Binance public endpoints)

Paid (require API keys in .env):
  Polygon.io    → stocks, options, forex, crypto (POLYGON_API_KEY)
  Alpha Vantage → stocks, forex, crypto (ALPHA_VANTAGE_API_KEY)
  Alpaca        → stocks, crypto (ALPACA_API_KEY + ALPACA_API_SECRET)

All fetch functions are async and share the same OHLCVBar return type.
Results are cached in Redis for 1h to avoid redundant upstream calls.

Heavy third-party imports are done lazily so the app starts even when
optional packages are absent in dev environments.
"""

from __future__ import annotations

import hashlib
import io
import json
from datetime import datetime
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    import pandas as pd

from schemas.data import OHLCVBar

# Timeframe translation tables
_YF_INTERVAL = {
    "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
    "1h": "1h", "4h": "4h", "1d": "1d", "1w": "1wk", "1M": "1mo",
}

_CCXT_TIMEFRAME = {
    "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
    "1h": "1h", "4h": "4h", "1d": "1d", "1w": "1w", "1M": "1M",
}

# Polygon multiplier/timespan from our token
_POLYGON_TIMESPAN: dict[str, tuple[int, str]] = {
    "1m":  (1,  "minute"),
    "5m":  (5,  "minute"),
    "15m": (15, "minute"),
    "30m": (30, "minute"),
    "1h":  (1,  "hour"),
    "4h":  (4,  "hour"),
    "1d":  (1,  "day"),
    "1w":  (1,  "week"),
    "1M":  (1,  "month"),
}

# Alpha Vantage function + outputsize mapping
_AV_FUNCTION = {
    "1m":  ("TIME_SERIES_INTRADAY", "1min"),
    "5m":  ("TIME_SERIES_INTRADAY", "5min"),
    "15m": ("TIME_SERIES_INTRADAY", "15min"),
    "30m": ("TIME_SERIES_INTRADAY", "30min"),
    "1h":  ("TIME_SERIES_INTRADAY", "60min"),
    "1d":  ("TIME_SERIES_DAILY_ADJUSTED", None),
    "1w":  ("TIME_SERIES_WEEKLY_ADJUSTED", None),
    "1M":  ("TIME_SERIES_MONTHLY_ADJUSTED", None),
}

# Alpaca timeframe mapping
_ALPACA_TIMEFRAME = {
    "1m": "1Min", "5m": "5Min", "15m": "15Min", "30m": "30Min",
    "1h": "1Hour", "4h": "4Hour", "1d": "1Day", "1w": "1Week", "1M": "1Month",
}

_CACHE_TTL = 3600  # 1 hour


# ── Cache helpers ──────────────────────────────────────────────────────────────

def _cache_key(source: str, symbol: str, timeframe: str, start: str, end: str) -> str:
    raw = f"{source}:{symbol}:{timeframe}:{start}:{end}"
    return "ohlcv:" + hashlib.md5(raw.encode()).hexdigest()


async def _cache_get(key: str) -> Optional[list[OHLCVBar]]:
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


async def _cache_set(key: str, bars: list[OHLCVBar]) -> None:
    try:
        import redis.asyncio as aioredis
        from config import settings
        r = aioredis.from_url(settings.redis_url, decode_responses=True)
        await r.setex(key, _CACHE_TTL, json.dumps([b.model_dump() for b in bars]))
        await r.aclose()
    except Exception:
        pass


# ── DataFrame → OHLCVBar ──────────────────────────────────────────────────────

def _df_to_bars(df: "pd.DataFrame") -> list[OHLCVBar]:
    import pandas as pd  # noqa: F811

    df = df.copy()
    df.columns = [c.lower() for c in df.columns]

    if df.index.name and df.index.name.lower() in ("date", "datetime", "timestamp"):
        df = df.reset_index()
        ts_col = df.columns[0]
    else:
        ts_col = next(c for c in df.columns if c in ("date", "datetime", "timestamp", "time"))

    df[ts_col] = pd.to_datetime(df[ts_col])
    df["ts_ms"] = df[ts_col].astype("int64") // 1_000_000

    bars = []
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


# ── Free connectors ───────────────────────────────────────────────────────────

async def fetch_yahoo(
    symbol: str,
    timeframe: str,
    start_date: str,
    end_date: str,
) -> list[OHLCVBar]:
    """Yahoo Finance via yfinance — stocks, ETFs, indices."""
    key = _cache_key("yahoo", symbol, timeframe, start_date, end_date)
    cached = await _cache_get(key)
    if cached is not None:
        return cached

    import yfinance as yf
    interval = _YF_INTERVAL.get(timeframe, "1d")
    df = yf.Ticker(symbol).history(interval=interval, start=start_date, end=end_date, auto_adjust=True)
    if df.empty:
        return []
    bars = _df_to_bars(df)
    await _cache_set(key, bars)
    return bars


async def fetch_binance(
    symbol: str,
    timeframe: str,
    start_date: str,
    end_date: str,
) -> list[OHLCVBar]:
    """Binance via ccxt — crypto."""
    key = _cache_key("binance", symbol, timeframe, start_date, end_date)
    cached = await _cache_get(key)
    if cached is not None:
        return cached

    import ccxt
    exchange = ccxt.binance({"enableRateLimit": True})
    tf = _CCXT_TIMEFRAME.get(timeframe, "1d")

    since_ms = int(datetime.fromisoformat(start_date).timestamp() * 1000)
    until_ms = int(datetime.fromisoformat(end_date).timestamp() * 1000)

    all_ohlcv: list[list] = []
    while True:
        batch = exchange.fetch_ohlcv(symbol, tf, since=since_ms, limit=1000)
        if not batch:
            break
        all_ohlcv.extend(batch)
        last_ts = batch[-1][0]
        if last_ts >= until_ms or len(batch) < 1000:
            break
        since_ms = last_ts + 1

    bars = []
    for row in all_ohlcv:
        ts, o, h, l, c, v = row
        if ts > until_ms:
            break
        bars.append(OHLCVBar(timestamp=ts, open=o, high=h, low=l, close=c, volume=v))

    await _cache_set(key, bars)
    return bars


# ── Paid connectors ───────────────────────────────────────────────────────────

async def fetch_polygon(
    symbol: str,
    timeframe: str,
    start_date: str,
    end_date: str,
) -> list[OHLCVBar]:
    """
    Polygon.io REST API — stocks, options, forex, crypto.
    Requires POLYGON_API_KEY in .env.
    Handles pagination automatically (next_url cursor).
    """
    from config import settings
    if not settings.polygon_api_key:
        raise ValueError("POLYGON_API_KEY not configured")

    key = _cache_key("polygon", symbol, timeframe, start_date, end_date)
    cached = await _cache_get(key)
    if cached is not None:
        return cached

    import httpx

    multiplier, timespan = _POLYGON_TIMESPAN.get(timeframe, (1, "day"))
    base = "https://api.polygon.io"
    url = (
        f"{base}/v2/aggs/ticker/{symbol}/range/{multiplier}/{timespan}"
        f"/{start_date}/{end_date}"
        f"?adjusted=true&sort=asc&limit=50000&apiKey={settings.polygon_api_key}"
    )

    bars: list[OHLCVBar] = []
    async with httpx.AsyncClient(timeout=30) as client:
        while url:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            for r in data.get("results", []):
                bars.append(OHLCVBar(
                    timestamp=int(r["t"]),
                    open=float(r["o"]),
                    high=float(r["h"]),
                    low=float(r["l"]),
                    close=float(r["c"]),
                    volume=float(r["v"]),
                ))
            # Polygon returns next_url for paginated results
            next_url = data.get("next_url")
            url = f"{next_url}&apiKey={settings.polygon_api_key}" if next_url else None

    await _cache_set(key, bars)
    return bars


async def fetch_alpha_vantage(
    symbol: str,
    timeframe: str,
    start_date: str,
    end_date: str,
) -> list[OHLCVBar]:
    """
    Alpha Vantage REST API — stocks, forex, crypto.
    Requires ALPHA_VANTAGE_API_KEY in .env.
    Daily/weekly/monthly use adjusted close for accuracy.
    Filters to [start_date, end_date].
    """
    from config import settings
    if not settings.alpha_vantage_api_key:
        raise ValueError("ALPHA_VANTAGE_API_KEY not configured")

    key = _cache_key("alpha_vantage", symbol, timeframe, start_date, end_date)
    cached = await _cache_get(key)
    if cached is not None:
        return cached

    import httpx
    import pandas as pd

    function, interval = _AV_FUNCTION.get(timeframe, ("TIME_SERIES_DAILY_ADJUSTED", None))
    params: dict[str, str] = {
        "function": function,
        "symbol": symbol,
        "outputsize": "full",
        "apikey": settings.alpha_vantage_api_key,
        "datatype": "json",
    }
    if interval:
        params["interval"] = interval

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get("https://www.alphavantage.co/query", params=params)
        resp.raise_for_status()
        data = resp.json()

    # AV returns the time series under a dynamic key, find it
    ts_key = next((k for k in data if "Time Series" in k), None)
    if not ts_key:
        raise ValueError(f"Alpha Vantage error: {data.get('Note') or data.get('Information') or 'unknown'}")

    ts = data[ts_key]
    start_dt = datetime.fromisoformat(start_date)
    end_dt   = datetime.fromisoformat(end_date)

    rows = []
    for date_str, vals in ts.items():
        dt = datetime.fromisoformat(date_str.split(" ")[0])
        if not (start_dt <= dt <= end_dt):
            continue
        ts_ms = int(dt.timestamp() * 1000)
        # AV uses "1. open", "4. close" or "5. adjusted close"
        open_  = float(vals.get("1. open",  vals.get("1. open",  0)))
        high   = float(vals.get("2. high",  0))
        low    = float(vals.get("3. low",   0))
        close  = float(vals.get("5. adjusted close", vals.get("4. close", 0)))
        volume = float(vals.get("6. volume", vals.get("5. volume", 0)))
        rows.append(OHLCVBar(timestamp=ts_ms, open=open_, high=high, low=low, close=close, volume=volume))

    # AV returns newest-first; sort ascending
    bars = sorted(rows, key=lambda b: b.timestamp)
    await _cache_set(key, bars)
    return bars


async def fetch_alpaca(
    symbol: str,
    timeframe: str,
    start_date: str,
    end_date: str,
) -> list[OHLCVBar]:
    """
    Alpaca Markets data API — stocks and crypto.
    Requires ALPACA_API_KEY + ALPACA_API_SECRET in .env.
    Handles pagination via next_page_token.
    """
    from config import settings
    if not settings.alpaca_api_key or not settings.alpaca_api_secret:
        raise ValueError("ALPACA_API_KEY / ALPACA_API_SECRET not configured")

    key = _cache_key("alpaca", symbol, timeframe, start_date, end_date)
    cached = await _cache_get(key)
    if cached is not None:
        return cached

    import httpx

    tf = _ALPACA_TIMEFRAME.get(timeframe, "1Day")
    headers = {
        "APCA-API-KEY-ID":     settings.alpaca_api_key,
        "APCA-API-SECRET-KEY": settings.alpaca_api_secret,
    }
    url = f"{settings.alpaca_base_url}/v2/stocks/{symbol}/bars"
    params: dict[str, str] = {
        "timeframe": tf,
        "start":     f"{start_date}T00:00:00Z",
        "end":       f"{end_date}T23:59:59Z",
        "limit":     "10000",
        "adjustment": "all",
        "feed":      "sip",
    }

    bars: list[OHLCVBar] = []
    async with httpx.AsyncClient(timeout=30) as client:
        while True:
            resp = await client.get(url, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()
            for r in data.get("bars", []):
                ts_ms = int(datetime.fromisoformat(r["t"].replace("Z", "+00:00")).timestamp() * 1000)
                bars.append(OHLCVBar(
                    timestamp=ts_ms,
                    open=float(r["o"]),
                    high=float(r["h"]),
                    low=float(r["l"]),
                    close=float(r["c"]),
                    volume=float(r["v"]),
                ))
            token = data.get("next_page_token")
            if not token:
                break
            params["page_token"] = token

    await _cache_set(key, bars)
    return bars


# ── CSV ───────────────────────────────────────────────────────────────────────

def parse_csv(content: bytes) -> tuple[list[OHLCVBar], list[str]]:
    """
    Parse a CSV file and return (bars, column_names).
    Expects columns: timestamp/date, open, high, low, close, volume (case-insensitive).
    """
    import pandas as pd
    df = pd.read_csv(io.BytesIO(content))
    columns = list(df.columns)
    bars = _df_to_bars(df)
    return bars, columns
