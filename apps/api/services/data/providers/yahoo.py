"""Yahoo Finance provider via yfinance — stocks, ETFs, indices, forex."""
from __future__ import annotations

from schemas.data import OHLCVBar, SymbolSearchResult
from services.data.protocol import cache_get, cache_set, df_to_bars, make_cache_key

_INTERVAL_MAP = {
    "1m": "1m",  "5m": "5m",  "15m": "15m", "30m": "30m",
    "1h": "1h",  "4h": "4h",  "1d": "1d",   "1w": "1wk", "1M": "1mo",
}


class YahooProvider:
    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        start_date: str,
        end_date: str,
    ) -> list[OHLCVBar]:
        key = make_cache_key("yahoo", symbol, timeframe, start_date, end_date)
        cached = await cache_get(key)
        if cached is not None:
            return cached

        import yfinance as yf

        interval = _INTERVAL_MAP.get(timeframe, "1d")
        df = yf.Ticker(symbol).history(
            interval=interval,
            start=start_date,
            end=end_date,
            auto_adjust=True,
        )
        if df.empty:
            return []

        bars = df_to_bars(df)
        await cache_set(key, bars)
        return bars

    async def search(self, query: str) -> list[SymbolSearchResult]:
        # yfinance has no public search endpoint; router uses its own catalog
        return []
