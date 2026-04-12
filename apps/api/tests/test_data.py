"""
Data route tests — symbol search and CSV upload.
Fetch tests (yfinance/ccxt) are skipped in CI since they hit live APIs.
"""

import io
import pytest
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_symbol_search_crypto(client):
    resp = await client.get("/data/search?q=BTC")
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) > 0
    assert any(r["symbol"] == "BTC/USDT" for r in results)


@pytest.mark.asyncio
async def test_symbol_search_filtered_by_asset_class(client):
    resp = await client.get("/data/search?q=EUR&asset_class=forex")
    assert resp.status_code == 200
    results = resp.json()
    assert all(r["asset_class"] == "forex" for r in results)


@pytest.mark.asyncio
async def test_symbol_search_no_results(client):
    resp = await client.get("/data/search?q=ZZZNOTREAL")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_upload_csv_valid(client):
    csv_content = (
        "timestamp,open,high,low,close,volume\n"
        "2024-01-01,42000,43000,41500,42800,1200.5\n"
        "2024-01-02,42800,44000,42500,43500,980.3\n"
        "2024-01-03,43500,43800,42000,42200,1100.0\n"
    ).encode()

    resp = await client.post(
        "/data/upload",
        files={"file": ("btc_daily.csv", io.BytesIO(csv_content), "text/csv")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["row_count"] == 3
    assert "timestamp" in data["columns"]
    assert "close" in data["columns"]


@pytest.mark.asyncio
async def test_upload_non_csv_rejected(client):
    resp = await client.post(
        "/data/upload",
        files={"file": ("data.json", io.BytesIO(b'{"a":1}'), "application/json")},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_upload_malformed_csv(client):
    bad_csv = b"this,is,not,ohlcv,data\nfoo,bar,baz,qux,quux\n"
    resp = await client.post(
        "/data/upload",
        files={"file": ("bad.csv", io.BytesIO(bad_csv), "text/csv")},
    )
    assert resp.status_code == 422
