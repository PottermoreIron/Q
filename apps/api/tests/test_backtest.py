"""
Backtest run tests.

Engine tests use synthetic OHLCV data — no live API calls.
Integration tests mock the data-provider layer via get_provider().
"""

import pytest
import numpy as np
import pandas as pd
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from unittest.mock import AsyncMock, MagicMock, patch

from database import Base, get_db
from main import app
from schemas.data import OHLCVBar
from services.engines._runtime import run_strategy
from services.engines.exceptions import EngineError
from services.metrics import compute_metrics


# ── Synthetic fixtures ────────────────────────────────────────────────────────

def _make_ohlcv(n: int = 200, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = 100 * np.cumprod(1 + rng.normal(0.001, 0.02, n))
    df = pd.DataFrame({
        "open":   close * (1 + rng.normal(0, 0.005, n)),
        "high":   close * (1 + np.abs(rng.normal(0, 0.01, n))),
        "low":    close * (1 - np.abs(rng.normal(0, 0.01, n))),
        "close":  close,
        "volume": rng.uniform(1000, 10000, n),
    }, index=pd.date_range("2022-01-01", periods=n, freq="D"))
    return df


def _make_bars(n: int = 200) -> list[OHLCVBar]:
    base_ms = 1672531200000
    return [
        OHLCVBar(
            timestamp=base_ms + i * 86400000,
            open=100.0, high=105.0, low=95.0,
            close=100.0 + i * 0.5, volume=1000.0,
        )
        for i in range(n)
    ]


_SIMPLE_STRATEGY = """\
import pandas as pd

def run(ohlcv):
    close = ohlcv["close"]
    fast = close.ewm(span=5, adjust=False).mean()
    slow = close.ewm(span=20, adjust=False).mean()
    entries = fast > slow
    exits   = fast < slow
    return {"entries": entries, "exits": exits}
"""


# ── Unit: metrics ─────────────────────────────────────────────────────────────

def test_metrics_basic():
    equity = pd.Series([100_000, 105_000, 102_000, 108_000, 115_000])
    trades = [{"pnl": 5000}, {"pnl": -3000}, {"pnl": 6000}, {"pnl": 7000}]
    m = compute_metrics(equity, trades)
    assert m["final_value"] == pytest.approx(115_000)
    assert m["win_rate"] == pytest.approx(0.75)
    assert m["max_drawdown"] < 0
    assert m["total_trades"] == 4


def test_metrics_empty_equity():
    m = compute_metrics(pd.Series(dtype=float), [])
    assert m["sharpe_ratio"] is None


def test_metrics_no_trades():
    equity = pd.Series([100_000.0] * 50)
    m = compute_metrics(equity, [])
    assert m["win_rate"] is None
    assert m["total_trades"] is None


# ── Unit: simple engine ───────────────────────────────────────────────────────

def test_engine_runs_strategy():
    df = _make_ohlcv(200)
    metrics, trades, equity = run_strategy(_SIMPLE_STRATEGY, df)
    assert metrics["final_value"] is not None
    assert len(equity) == 200
    assert isinstance(trades, list)


def test_engine_rejects_forbidden_code():
    bad_code = "import os\ndef run(ohlcv):\n    return {}\n"
    with pytest.raises(EngineError, match="Validation failed"):
        run_strategy(bad_code, _make_ohlcv(50))


def test_engine_rejects_runtime_error():
    code = (
        "import pandas as pd\n"
        "def run(ohlcv):\n"
        "    raise ValueError('boom')\n"
    )
    with pytest.raises(EngineError, match="runtime error"):
        run_strategy(code, _make_ohlcv(50))


def test_engine_empty_signals():
    code = (
        "import pandas as pd\n"
        "def run(ohlcv):\n"
        "    close = ohlcv['close']\n"
        "    return {'entries': pd.Series(False, index=close.index),\n"
        "            'exits':   pd.Series(False, index=close.index)}\n"
    )
    metrics, trades, equity = run_strategy(code, _make_ohlcv(100))
    assert len(trades) == 0
    assert metrics["final_value"] == pytest.approx(100_000.0)


# ── Integration: API ──────────────────────────────────────────────────────────

@pytest.fixture
async def client(db: AsyncSession):
    """HTTP client wired to the real-PG db fixture from conftest."""
    async def override():
        yield db
    app.dependency_overrides[get_db] = override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


def _mock_provider(bars: list[OHLCVBar]):
    provider = MagicMock()
    provider.fetch_ohlcv = AsyncMock(return_value=bars)
    return provider


async def _create_strategy(client, code: str = _SIMPLE_STRATEGY) -> str:
    resp = await client.post("/strategies", json={
        "name": "Test Strategy",
        "blocks": [],
        "python_code": code,
    })
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_create_run_inline(client):
    """Inline run with mocked data-provider layer."""
    sid = await _create_strategy(client)
    with patch("routers.backtest.get_provider", return_value=_mock_provider(_make_bars(200))):
        resp = await client.post("/backtests", json={
            "strategy_id": sid,
            "data_config": {
                "source": "yahoo", "symbol": "AAPL",
                "asset_class": "stock", "timeframe": "1d",
                "start_date": "2022-01-01", "end_date": "2022-12-31",
            },
        })
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "completed"
    assert data["metrics"] is not None
    assert data["metrics"]["final_value"] is not None


@pytest.mark.asyncio
async def test_create_run_no_data(client):
    sid = await _create_strategy(client)
    with patch("routers.backtest.get_provider", return_value=_mock_provider([])):
        resp = await client.post("/backtests", json={
            "strategy_id": sid,
            "data_config": {
                "source": "yahoo", "symbol": "AAPL",
                "asset_class": "stock", "timeframe": "1d",
                "start_date": "2022-01-01", "end_date": "2022-12-31",
            },
        })
    assert resp.status_code == 201
    assert resp.json()["status"] == "failed"


@pytest.mark.asyncio
async def test_get_run(client):
    sid = await _create_strategy(client)
    with patch("routers.backtest.get_provider", return_value=_mock_provider(_make_bars(100))):
        create = await client.post("/backtests", json={
            "strategy_id": sid,
            "data_config": {
                "source": "yahoo", "symbol": "AAPL",
                "asset_class": "stock", "timeframe": "1d",
                "start_date": "2022-01-01", "end_date": "2022-06-30",
            },
        })
    run_id = create.json()["id"]
    resp = await client.get(f"/backtests/{run_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == run_id


@pytest.mark.asyncio
async def test_list_runs(client):
    resp = await client.get("/backtests")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_delete_run(client):
    sid = await _create_strategy(client)
    with patch("routers.backtest.get_provider", return_value=_mock_provider(_make_bars(50))):
        create = await client.post("/backtests", json={
            "strategy_id": sid,
            "data_config": {
                "source": "yahoo", "symbol": "AAPL",
                "asset_class": "stock", "timeframe": "1d",
                "start_date": "2022-01-01", "end_date": "2022-03-31",
            },
        })
    run_id = create.json()["id"]
    del_resp = await client.delete(f"/backtests/{run_id}")
    assert del_resp.status_code == 204
    get_resp = await client.get(f"/backtests/{run_id}")
    assert get_resp.status_code == 404
