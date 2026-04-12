"""
Data ingestion connectors.

yfinance  → stocks (Yahoo Finance, free)
ccxt      → crypto (Binance and others, free public endpoints)

Heavy dependencies (yfinance, ccxt) are imported lazily so the app starts
even if they are not installed in dev environments that skip optional deps.
"""

from __future__ import annotations

import io
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd

from schemas.data import OHLCVBar

# Mapping from our timeframe tokens to yfinance intervals
_YF_INTERVAL = {
    "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
    "1h": "1h", "4h": "4h", "1d": "1d", "1w": "1wk", "1M": "1mo",
}

# Mapping from our timeframe tokens to ccxt timeframes
_CCXT_TIMEFRAME = {
    "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
    "1h": "1h", "4h": "4h", "1d": "1d", "1w": "1w", "1M": "1M",
}


def _df_to_bars(df: "pd.DataFrame") -> list[OHLCVBar]:
    """Convert a DataFrame with OHLCV columns to OHLCVBar list."""
    import pandas as pd  # noqa: F811

    df = df.copy()
    df.columns = [c.lower() for c in df.columns]

    # Normalise timestamp column
    if df.index.name and df.index.name.lower() in ("date", "datetime", "timestamp"):
        df = df.reset_index()
        ts_col = df.columns[0]
    else:
        ts_col = next(c for c in df.columns if c in ("date", "datetime", "timestamp", "time"))

    df[ts_col] = pd.to_datetime(df[ts_col])
    df["ts_ms"] = df[ts_col].astype("int64") // 1_000_000

    bars = []
    for row in df.itertuples(index=False):
        bars.append(
            OHLCVBar(
                timestamp=int(row.ts_ms),
                open=float(row.open),
                high=float(row.high),
                low=float(row.low),
                close=float(row.close),
                volume=float(row.volume),
            )
        )
    return bars


async def fetch_yahoo(
    symbol: str,
    timeframe: str,
    start_date: str,
    end_date: str,
) -> list[OHLCVBar]:
    """Fetch OHLCV from Yahoo Finance via yfinance (stocks, ETFs, indices)."""
    import yfinance as yf

    interval = _YF_INTERVAL.get(timeframe, "1d")
    ticker = yf.Ticker(symbol)
    df = ticker.history(interval=interval, start=start_date, end=end_date, auto_adjust=True)
    if df.empty:
        return []
    return _df_to_bars(df)


async def fetch_binance(
    symbol: str,
    timeframe: str,
    start_date: str,
    end_date: str,
) -> list[OHLCVBar]:
    """Fetch OHLCV from Binance via ccxt (crypto)."""
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
    return bars


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
