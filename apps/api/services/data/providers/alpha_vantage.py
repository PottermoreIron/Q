"""Alpha Vantage provider — stocks, forex, crypto. Requires ALPHA_VANTAGE_API_KEY."""
from __future__ import annotations

from datetime import datetime

from schemas.data import OHLCVBar, SymbolSearchResult
from services.data.protocol import cache_get, cache_set, make_cache_key

# (function_name, interval_param | None)
_FUNCTION_MAP: dict[str, tuple[str, str | None]] = {
    "1m":  ("TIME_SERIES_INTRADAY",         "1min"),
    "5m":  ("TIME_SERIES_INTRADAY",         "5min"),
    "15m": ("TIME_SERIES_INTRADAY",         "15min"),
    "30m": ("TIME_SERIES_INTRADAY",         "30min"),
    "1h":  ("TIME_SERIES_INTRADAY",         "60min"),
    "1d":  ("TIME_SERIES_DAILY_ADJUSTED",   None),
    "1w":  ("TIME_SERIES_WEEKLY_ADJUSTED",  None),
    "1M":  ("TIME_SERIES_MONTHLY_ADJUSTED", None),
}


class AlphaVantageProvider:
    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        start_date: str,
        end_date: str,
    ) -> list[OHLCVBar]:
        from config import settings
        if not settings.alpha_vantage_api_key:
            raise ValueError("ALPHA_VANTAGE_API_KEY not configured")

        key = make_cache_key("alpha_vantage", symbol, timeframe, start_date, end_date)
        cached = await cache_get(key)
        if cached is not None:
            return cached

        import httpx

        function, interval = _FUNCTION_MAP.get(timeframe, ("TIME_SERIES_DAILY_ADJUSTED", None))
        params: dict[str, str] = {
            "function":   function,
            "symbol":     symbol,
            "outputsize": "full",
            "apikey":     settings.alpha_vantage_api_key,
            "datatype":   "json",
        }
        if interval:
            params["interval"] = interval

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get("https://www.alphavantage.co/query", params=params)
            resp.raise_for_status()
            data = resp.json()

        ts_key = next((k for k in data if "Time Series" in k), None)
        if not ts_key:
            note = data.get("Note") or data.get("Information") or "unknown error"
            raise ValueError(f"Alpha Vantage: {note}")

        start_dt = datetime.fromisoformat(start_date)
        end_dt   = datetime.fromisoformat(end_date)

        rows: list[OHLCVBar] = []
        for date_str, vals in data[ts_key].items():
            dt = datetime.fromisoformat(date_str.split(" ")[0])
            if not (start_dt <= dt <= end_dt):
                continue
            ts_ms = int(dt.timestamp() * 1000)
            rows.append(OHLCVBar(
                timestamp=ts_ms,
                open=float(vals.get("1. open", 0)),
                high=float(vals.get("2. high", 0)),
                low=float(vals.get("3. low", 0)),
                # prefer adjusted close when present
                close=float(vals.get("5. adjusted close", vals.get("4. close", 0))),
                volume=float(vals.get("6. volume", vals.get("5. volume", 0))),
            ))

        bars = sorted(rows, key=lambda b: b.timestamp)  # AV returns newest-first
        await cache_set(key, bars)
        return bars

    async def search(self, query: str) -> list[SymbolSearchResult]:
        return []
