"""Alpaca Markets data provider — stocks, crypto. Requires ALPACA_API_KEY + SECRET."""
from __future__ import annotations

from datetime import datetime

from schemas.data import OHLCVBar, SymbolSearchResult
from services.data.protocol import cache_get, cache_set, make_cache_key

_TIMEFRAME_MAP = {
    "1m": "1Min",  "5m": "5Min",  "15m": "15Min", "30m": "30Min",
    "1h": "1Hour", "4h": "4Hour", "1d": "1Day",   "1w": "1Week",  "1M": "1Month",
}


class AlpacaProvider:
    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        start_date: str,
        end_date: str,
    ) -> list[OHLCVBar]:
        from config import settings
        if not settings.alpaca_api_key or not settings.alpaca_api_secret:
            raise ValueError("ALPACA_API_KEY / ALPACA_API_SECRET not configured")

        key = make_cache_key("alpaca", symbol, timeframe, start_date, end_date)
        cached = await cache_get(key)
        if cached is not None:
            return cached

        import httpx

        headers = {
            "APCA-API-KEY-ID":     settings.alpaca_api_key,
            "APCA-API-SECRET-KEY": settings.alpaca_api_secret,
        }
        params: dict[str, str] = {
            "timeframe":  _TIMEFRAME_MAP.get(timeframe, "1Day"),
            "start":      f"{start_date}T00:00:00Z",
            "end":        f"{end_date}T23:59:59Z",
            "limit":      "10000",
            "adjustment": "all",
            "feed":       "sip",
        }
        url = f"{settings.alpaca_base_url}/v2/stocks/{symbol}/bars"

        bars: list[OHLCVBar] = []
        async with httpx.AsyncClient(timeout=30) as client:
            while True:
                resp = await client.get(url, headers=headers, params=params)
                resp.raise_for_status()
                data = resp.json()
                for r in data.get("bars", []):
                    ts_ms = int(
                        datetime.fromisoformat(r["t"].replace("Z", "+00:00")).timestamp() * 1000
                    )
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

        await cache_set(key, bars)
        return bars

    async def search(self, query: str) -> list[SymbolSearchResult]:
        return []
