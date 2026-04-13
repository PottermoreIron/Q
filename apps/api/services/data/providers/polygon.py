"""Polygon.io provider — stocks, forex, crypto. Requires POLYGON_API_KEY."""
from __future__ import annotations

from schemas.data import OHLCVBar, SymbolSearchResult
from services.data.protocol import cache_get, cache_set, make_cache_key

_TIMESPAN_MAP: dict[str, tuple[int, str]] = {
    "1m":  (1,  "minute"), "5m":  (5,  "minute"),
    "15m": (15, "minute"), "30m": (30, "minute"),
    "1h":  (1,  "hour"),   "4h":  (4,  "hour"),
    "1d":  (1,  "day"),    "1w":  (1,  "week"),  "1M": (1, "month"),
}


class PolygonProvider:
    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        start_date: str,
        end_date: str,
    ) -> list[OHLCVBar]:
        from config import settings
        if not settings.polygon_api_key:
            raise ValueError("POLYGON_API_KEY not configured")

        key = make_cache_key("polygon", symbol, timeframe, start_date, end_date)
        cached = await cache_get(key)
        if cached is not None:
            return cached

        import httpx

        multiplier, timespan = _TIMESPAN_MAP.get(timeframe, (1, "day"))
        base_url = (
            f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range"
            f"/{multiplier}/{timespan}/{start_date}/{end_date}"
            f"?adjusted=true&sort=asc&limit=50000&apiKey={settings.polygon_api_key}"
        )

        bars: list[OHLCVBar] = []
        url: str | None = base_url
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
                next_url = data.get("next_url")
                url = f"{next_url}&apiKey={settings.polygon_api_key}" if next_url else None

        await cache_set(key, bars)
        return bars

    async def search(self, query: str) -> list[SymbolSearchResult]:
        return []
