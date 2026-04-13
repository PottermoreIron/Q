"""
AkShare provider — Chinese A-shares, HK stocks, Chinese futures.

Free, no API key, no registration. Covers markets that yfinance misses entirely.
Install: pip install akshare

Symbol conventions understood by this provider:
  A-shares:   6-digit numeric code          → "000001", "600519"
  HK stocks:  "HK" prefix + 5-digit code   → "HK00700", "HK09988"
  US stocks:  explicit source="akshare" with standard ticker → "AAPL"

Intraday not supported by akshare's free tier; supported timeframes: 1d, 1w, 1M.
Column names returned by akshare are in Chinese; translation is the corruption
layer — domain code never sees "日期", "开盘", etc.
"""
from __future__ import annotations

import asyncio

from schemas.data import OHLCVBar, SymbolSearchResult
from services.data.protocol import cache_get, cache_set, make_cache_key

_PERIOD_MAP = {
    "1d": "daily",
    "1w": "weekly",
    "1M": "monthly",
}

# Chinese column → our domain name  (A-shares and HK shares share the same schema)
_COL_ZH = {
    "日期": "date",
    "开盘": "open",
    "收盘": "close",
    "最高": "high",
    "最低": "low",
    "成交量": "volume",
}


class AkShareProvider:
    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        start_date: str,
        end_date: str,
    ) -> list[OHLCVBar]:
        if timeframe not in _PERIOD_MAP:
            raise ValueError(
                f"AkShare supports daily/weekly/monthly only; '{timeframe}' is not supported. "
                "Use source='yahoo' for intraday data."
            )

        key = make_cache_key("akshare", symbol, timeframe, start_date, end_date)
        cached = await cache_get(key)
        if cached is not None:
            return cached

        import akshare as ak

        period = _PERIOD_MAP[timeframe]
        # akshare date params: "YYYYMMDD"
        start_str = start_date.replace("-", "")
        end_str   = end_date.replace("-", "")

        if symbol.isdigit() and len(symbol) == 6:
            # A-share stock
            df = await asyncio.to_thread(
                ak.stock_zh_a_hist,
                symbol=symbol,
                period=period,
                start_date=start_str,
                end_date=end_str,
                adjust="qfq",  # forward-adjusted for splits/dividends
            )
            df = df.rename(columns=_COL_ZH)

        elif symbol.upper().startswith("HK") and symbol[2:].isdigit():
            # HK stock: "HK00700" → code "00700"
            hk_code = symbol[2:]
            df = await asyncio.to_thread(
                ak.stock_hk_hist,
                symbol=hk_code,
                period=period,
                start_date=start_str,
                end_date=end_str,
                adjust="qfq",
            )
            df = df.rename(columns=_COL_ZH)

        else:
            # US stocks via eastmoney mirror (no auth required, best-effort)
            df = await asyncio.to_thread(
                ak.stock_us_hist,
                symbol=symbol,
                period=period,
                start_date=start_str,
                end_date=end_str,
                adjust="qfq",
            )
            df = df.rename(columns=_COL_ZH)

        if df.empty:
            return []

        bars = _df_to_bars(df)
        await cache_set(key, bars)
        return bars

    async def search(self, query: str) -> list[SymbolSearchResult]:
        # akshare exposes stock lists but not free-text search; return empty
        # so the router falls back to its own catalog
        return []


def _df_to_bars(df) -> list[OHLCVBar]:
    """Translate akshare DataFrame (post-rename) to OHLCVBar list."""
    import pandas as pd

    df = df.copy()
    # After rename: "date", "open", "close", "high", "low", "volume" present
    df["date"] = pd.to_datetime(df["date"], utc=True)
    ts_ms = df["date"].astype("int64") // 1_000_000

    return [
        OHLCVBar(
            timestamp=int(ts),
            open=float(row.open),
            high=float(row.high),
            low=float(row.low),
            close=float(row.close),
            volume=float(row.volume),
        )
        for ts, row in zip(ts_ms, df.itertuples(index=False))
    ]
