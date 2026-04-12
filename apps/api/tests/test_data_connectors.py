"""
Unit tests for paid data connectors and cache key helpers.

All external HTTP calls are mocked — no live API keys required.
Redis cache is bypassed (cache_get returns None, cache_set is a no-op).

settings is patched at config.settings because the connectors import it
via `from config import settings` inside the function body.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from services.data_ingestion import (
    _cache_key,
    fetch_alpha_vantage,
    fetch_alpaca,
    fetch_polygon,
)

_NO_CACHE = {
    "services.data_ingestion._cache_get": dict(new_callable=AsyncMock, return_value=None),
    "services.data_ingestion._cache_set": dict(new_callable=AsyncMock),
}


def _mock_settings(**kwargs):
    s = MagicMock()
    for k, v in kwargs.items():
        setattr(s, k, v)
    return s


def _mock_http_client(*responses):
    """Return an async context manager whose .get() yields responses in order."""
    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    if len(responses) == 1:
        mock_resp = MagicMock()
        mock_resp.json.return_value = responses[0]
        mock_resp.raise_for_status = MagicMock()
        client.get = AsyncMock(return_value=mock_resp)
    else:
        mocks = []
        for r in responses:
            m = MagicMock()
            m.json.return_value = r
            m.raise_for_status = MagicMock()
            mocks.append(m)
        client.get = AsyncMock(side_effect=mocks)
    return client


# ── Cache key stability ────────────────────────────────────────────────────────

def test_cache_key_stable():
    k1 = _cache_key("yahoo", "AAPL", "1d", "2023-01-01", "2023-12-31")
    k2 = _cache_key("yahoo", "AAPL", "1d", "2023-01-01", "2023-12-31")
    assert k1 == k2
    assert k1.startswith("ohlcv:")


def test_cache_key_differs_by_source():
    k_yahoo   = _cache_key("yahoo",   "AAPL", "1d", "2023-01-01", "2023-12-31")
    k_polygon = _cache_key("polygon", "AAPL", "1d", "2023-01-01", "2023-12-31")
    assert k_yahoo != k_polygon


def test_cache_key_differs_by_symbol():
    k1 = _cache_key("yahoo", "AAPL", "1d", "2023-01-01", "2023-12-31")
    k2 = _cache_key("yahoo", "MSFT", "1d", "2023-01-01", "2023-12-31")
    assert k1 != k2


# ── Polygon connector ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_polygon_returns_bars():
    response = {
        "results": [
            {"t": 1672531200000, "o": 130.0, "h": 132.0, "l": 129.0, "c": 131.0, "v": 50000.0},
            {"t": 1672617600000, "o": 131.0, "h": 133.0, "l": 130.0, "c": 132.5, "v": 45000.0},
        ],
    }
    settings = _mock_settings(polygon_api_key="test-key")

    with patch("services.data_ingestion._cache_get", new_callable=AsyncMock, return_value=None), \
         patch("services.data_ingestion._cache_set", new_callable=AsyncMock), \
         patch("config.settings", settings), \
         patch("httpx.AsyncClient", return_value=_mock_http_client(response)):
        bars = await fetch_polygon("AAPL", "1d", "2023-01-01", "2023-12-31")

    assert len(bars) == 2
    assert bars[0].open == 130.0
    assert bars[1].close == 132.5


@pytest.mark.asyncio
async def test_fetch_polygon_no_api_key():
    settings = _mock_settings(polygon_api_key="")
    with patch("config.settings", settings):
        with pytest.raises(ValueError, match="POLYGON_API_KEY"):
            await fetch_polygon("AAPL", "1d", "2023-01-01", "2023-12-31")


@pytest.mark.asyncio
async def test_fetch_polygon_pagination():
    page1 = {
        "results": [{"t": 1672531200000, "o": 130.0, "h": 132.0, "l": 129.0, "c": 131.0, "v": 50000.0}],
        "next_url": "https://api.polygon.io/v2/aggs/next",
    }
    page2 = {
        "results": [{"t": 1672617600000, "o": 131.0, "h": 133.0, "l": 130.0, "c": 132.5, "v": 45000.0}],
    }
    settings = _mock_settings(polygon_api_key="test-key")
    client = _mock_http_client(page1, page2)

    with patch("services.data_ingestion._cache_get", new_callable=AsyncMock, return_value=None), \
         patch("services.data_ingestion._cache_set", new_callable=AsyncMock), \
         patch("config.settings", settings), \
         patch("httpx.AsyncClient", return_value=client):
        bars = await fetch_polygon("AAPL", "1d", "2023-01-01", "2023-12-31")

    assert len(bars) == 2
    assert client.get.call_count == 2


# ── Alpha Vantage connector ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_alpha_vantage_returns_bars():
    response = {
        "Time Series (Daily)": {
            "2023-06-02": {
                "1. open": "180.57", "2. high": "182.00", "3. low": "179.00",
                "5. adjusted close": "181.50", "6. volume": "62000000",
            },
            "2023-06-01": {
                "1. open": "178.00", "2. high": "180.00", "3. low": "177.50",
                "5. adjusted close": "179.80", "6. volume": "55000000",
            },
        }
    }
    settings = _mock_settings(alpha_vantage_api_key="test-key")

    with patch("services.data_ingestion._cache_get", new_callable=AsyncMock, return_value=None), \
         patch("services.data_ingestion._cache_set", new_callable=AsyncMock), \
         patch("config.settings", settings), \
         patch("httpx.AsyncClient", return_value=_mock_http_client(response)):
        bars = await fetch_alpha_vantage("AAPL", "1d", "2023-01-01", "2023-12-31")

    assert len(bars) == 2
    # sorted ascending by date
    assert bars[0].close == pytest.approx(179.80)
    assert bars[1].close == pytest.approx(181.50)


@pytest.mark.asyncio
async def test_fetch_alpha_vantage_no_api_key():
    settings = _mock_settings(alpha_vantage_api_key="")
    with patch("config.settings", settings):
        with pytest.raises(ValueError, match="ALPHA_VANTAGE_API_KEY"):
            await fetch_alpha_vantage("AAPL", "1d", "2023-01-01", "2023-12-31")


@pytest.mark.asyncio
async def test_fetch_alpha_vantage_rate_limit_error():
    response = {"Note": "Thank you for using Alpha Vantage! Our standard API call frequency is 5 calls per minute."}
    settings = _mock_settings(alpha_vantage_api_key="test-key")

    with patch("services.data_ingestion._cache_get", new_callable=AsyncMock, return_value=None), \
         patch("services.data_ingestion._cache_set", new_callable=AsyncMock), \
         patch("config.settings", settings), \
         patch("httpx.AsyncClient", return_value=_mock_http_client(response)):
        with pytest.raises(ValueError, match="Alpha Vantage error"):
            await fetch_alpha_vantage("AAPL", "1d", "2023-01-01", "2023-12-31")


# ── Alpaca connector ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_alpaca_returns_bars():
    response = {
        "bars": [
            {"t": "2023-01-03T05:00:00Z", "o": 130.28, "h": 130.90, "l": 124.17, "c": 125.07, "v": 112117500},
            {"t": "2023-01-04T05:00:00Z", "o": 126.89, "h": 128.66, "l": 125.08, "c": 126.36, "v": 89113600},
        ],
    }
    settings = _mock_settings(
        alpaca_api_key="test-key",
        alpaca_api_secret="test-secret",
        alpaca_base_url="https://data.alpaca.markets",
    )

    with patch("services.data_ingestion._cache_get", new_callable=AsyncMock, return_value=None), \
         patch("services.data_ingestion._cache_set", new_callable=AsyncMock), \
         patch("config.settings", settings), \
         patch("httpx.AsyncClient", return_value=_mock_http_client(response)):
        bars = await fetch_alpaca("AAPL", "1d", "2023-01-01", "2023-12-31")

    assert len(bars) == 2
    assert bars[0].open == pytest.approx(130.28)
    assert bars[1].close == pytest.approx(126.36)


@pytest.mark.asyncio
async def test_fetch_alpaca_no_api_key():
    settings = _mock_settings(alpaca_api_key="", alpaca_api_secret="")
    with patch("config.settings", settings):
        with pytest.raises(ValueError, match="ALPACA_API_KEY"):
            await fetch_alpaca("AAPL", "1d", "2023-01-01", "2023-12-31")


@pytest.mark.asyncio
async def test_fetch_alpaca_pagination():
    page1 = {
        "bars": [{"t": "2023-01-03T05:00:00Z", "o": 130.0, "h": 132.0, "l": 129.0, "c": 131.0, "v": 100}],
        "next_page_token": "abc123",
    }
    page2 = {
        "bars": [{"t": "2023-01-04T05:00:00Z", "o": 131.0, "h": 133.0, "l": 130.0, "c": 132.0, "v": 200}],
    }
    settings = _mock_settings(
        alpaca_api_key="test-key",
        alpaca_api_secret="test-secret",
        alpaca_base_url="https://data.alpaca.markets",
    )
    client = _mock_http_client(page1, page2)

    with patch("services.data_ingestion._cache_get", new_callable=AsyncMock, return_value=None), \
         patch("services.data_ingestion._cache_set", new_callable=AsyncMock), \
         patch("config.settings", settings), \
         patch("httpx.AsyncClient", return_value=client):
        bars = await fetch_alpaca("AAPL", "1d", "2023-01-01", "2023-12-31")

    assert len(bars) == 2
    assert client.get.call_count == 2
