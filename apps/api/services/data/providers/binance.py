"""Binance provider via ccxt — crypto spot pairs."""
from __future__ import annotations

from datetime import datetime

from schemas.data import OHLCVBar, SymbolSearchResult
from services.data.protocol import cache_get, cache_set, make_cache_key

_TIMEFRAME_MAP = {
    "1m": "1m",  "5m": "5m",  "15m": "15m", "30m": "30m",
    "1h": "1h",  "4h": "4h",  "1d": "1d",   "1w": "1w",  "1M": "1M",
}


class BinanceProvider:
    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        start_date: str,
        end_date: str,
    ) -> list[OHLCVBar]:
        key = make_cache_key("binance", symbol, timeframe, start_date, end_date)
        cached = await cache_get(key)
        if cached is not None:
            return cached

        import ccxt

        exchange = ccxt.binance({"enableRateLimit": True})
        tf = _TIMEFRAME_MAP.get(timeframe, "1d")

        since_ms = int(datetime.fromisoformat(start_date).timestamp() * 1000)
        until_ms = int(datetime.fromisoformat(end_date).timestamp() * 1000)

        raw: list[list] = []
        while True:
            batch = exchange.fetch_ohlcv(symbol, tf, since=since_ms, limit=1000)
            if not batch:
                break
            raw.extend(batch)
            last_ts = batch[-1][0]
            if last_ts >= until_ms or len(batch) < 1000:
                break
            since_ms = last_ts + 1

        bars: list[OHLCVBar] = []
        for ts, o, h, l, c, v in raw:
            if ts > until_ms:
                break
            bars.append(OHLCVBar(timestamp=ts, open=o, high=h, low=l, close=c, volume=v))

        await cache_set(key, bars)
        return bars

    async def search(self, query: str) -> list[SymbolSearchResult]:
        return []
