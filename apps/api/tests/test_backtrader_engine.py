"""
BacktraderEngine tests — Task 5.

All tests use synthetic data so they never hit the network.
Fill model: NextBarOpenFill (Backtrader default for stocks/forex).
"""

from __future__ import annotations

from typing import List

import numpy as np
import pandas as pd
import pytest

from schemas.data import OHLCVBar
from services.engines.exceptions import EngineError
from services.engines.execution_model import (
    AShareCommission,
    CurrentCloseDelayedFill,
    ExecutionConfig,
    FixedBpsSlippage,
    NextBarOpenFill,
    PercentageCommission,
    PerShareCommission,
    TieredCommission,
)
from services.engines.backtrader import BacktraderEngine


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_bars(n: int = 252, seed: int = 0) -> List[OHLCVBar]:
    rng = np.random.default_rng(seed)
    returns = rng.normal(0.0003, 0.015, n)
    close = 100.0 * np.exp(np.cumsum(returns))
    dates = pd.date_range("2022-01-03", periods=n, freq="B")
    bars = []
    for i in range(n):
        c = float(close[i])
        bars.append(OHLCVBar(
            timestamp=int(dates[i].timestamp() * 1000),
            open=c * (1 + rng.normal(0, 0.003)),
            high=c * (1 + abs(rng.normal(0, 0.008))),
            low=c * (1 - abs(rng.normal(0, 0.008))),
            close=c,
            volume=float(rng.uniform(1000, 10000)),
        ))
    return bars


_BUY_HOLD = """\
import pandas as pd

def run(ohlcv):
    entries = pd.Series(False, index=ohlcv.index)
    exits   = pd.Series(False, index=ohlcv.index)
    entries.iloc[0] = True
    exits.iloc[-2]  = True
    return {"entries": entries, "exits": exits}
"""

_EMA_CROSSOVER = """\
import pandas as pd

def run(ohlcv):
    close = ohlcv["close"]
    fast = close.ewm(span=10, adjust=False).mean()
    slow = close.ewm(span=30, adjust=False).mean()
    return {"entries": fast > slow, "exits": fast < slow}
"""

_NO_TRADES = """\
import pandas as pd

def run(ohlcv):
    return {
        "entries": pd.Series(False, index=ohlcv.index),
        "exits":   pd.Series(False, index=ohlcv.index),
    }
"""

_WITH_SL_TP = """\
import pandas as pd

def run(ohlcv):
    entries = pd.Series(False, index=ohlcv.index)
    exits   = pd.Series(False, index=ohlcv.index)
    entries.iloc[0] = True
    return {
        "entries": entries,
        "exits": exits,
        "stop_loss_pct": 0.05,
        "take_profit_pct": 0.20,
    }
"""


# ── Basic contract tests ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_result_shape_buy_hold():
    engine = BacktraderEngine()
    bars = _make_bars(100)
    result = await engine.run(_BUY_HOLD, bars)
    assert result.engine == "backtrader"
    assert isinstance(result.metrics, dict)
    assert isinstance(result.trades, list)
    assert isinstance(result.equity_curve, list)
    assert len(result.equity_curve) > 0


@pytest.mark.asyncio
async def test_equity_curve_length():
    bars = _make_bars(200)
    result = await BacktraderEngine().run(_BUY_HOLD, bars)
    assert 1 <= len(result.equity_curve) <= 300


@pytest.mark.asyncio
async def test_no_trades_result():
    bars = _make_bars(50)
    result = await BacktraderEngine().run(_NO_TRADES, bars)
    assert result.trades == [] or result.metrics.get("total_trades") is None
    assert result.metrics["final_value"] == pytest.approx(100_000.0, rel=1e-3)


@pytest.mark.asyncio
async def test_trade_fields_present():
    bars = _make_bars(100)
    result = await BacktraderEngine().run(_BUY_HOLD, bars)
    assert len(result.trades) >= 1
    t = result.trades[0]
    for field in ("entry_price", "exit_price", "pnl", "side", "fees",
                  "entry_time", "exit_time", "quantity", "pnl_pct",
                  "bars_held", "mae", "mfe"):
        assert field in t, f"missing field: {field}"


@pytest.mark.asyncio
async def test_trade_side_is_long():
    bars = _make_bars(100)
    result = await BacktraderEngine().run(_BUY_HOLD, bars)
    for t in result.trades:
        assert t["side"] == "long"


@pytest.mark.asyncio
async def test_pnl_pct_consistent_with_prices():
    bars = _make_bars(100)
    result = await BacktraderEngine().run(_BUY_HOLD, bars)
    assert len(result.trades) >= 1
    t = result.trades[0]
    expected_pct = (t["exit_price"] - t["entry_price"]) / t["entry_price"]
    assert t["pnl_pct"] == pytest.approx(expected_pct, rel=1e-3)


@pytest.mark.asyncio
async def test_bars_held_non_negative():
    bars = _make_bars(100)
    result = await BacktraderEngine().run(_EMA_CROSSOVER, bars)
    for t in result.trades:
        assert t["bars_held"] >= 0


@pytest.mark.asyncio
async def test_mae_le_zero_mfe_ge_zero():
    bars = _make_bars(252, seed=42)
    result = await BacktraderEngine().run(_EMA_CROSSOVER, bars)
    for t in result.trades:
        assert t["mae"] <= 1e-9, f"MAE should be ≤ 0, got {t['mae']}"
        assert t["mfe"] >= -1e-9, f"MFE should be ≥ 0, got {t['mfe']}"


@pytest.mark.asyncio
async def test_metrics_schema_version():
    bars = _make_bars(100)
    result = await BacktraderEngine().run(_BUY_HOLD, bars)
    assert result.metrics["schema_version"] == 2


@pytest.mark.asyncio
async def test_stop_loss_triggers():
    """A strategy with SL/TP should still produce valid results."""
    bars = _make_bars(252)
    result = await BacktraderEngine().run(_WITH_SL_TP, bars)
    assert result.engine == "backtrader"
    assert len(result.trades) >= 1


# ── Execution config — all models accepted ────────────────────────────────────

@pytest.mark.asyncio
async def test_accepts_percentage_commission():
    bars = _make_bars(100)
    cfg = ExecutionConfig(
        commission=PercentageCommission(rate=0.001),
        slippage=FixedBpsSlippage(bps=5),
        fill=NextBarOpenFill(),
    )
    result = await BacktraderEngine(execution_config=cfg).run(_BUY_HOLD, bars)
    assert result.engine == "backtrader"


@pytest.mark.asyncio
async def test_accepts_per_share_commission():
    bars = _make_bars(100)
    cfg = ExecutionConfig(
        commission=PerShareCommission(per_share=0.005, min_per_order=1.0),
        slippage=FixedBpsSlippage(bps=0),
        fill=NextBarOpenFill(),
    )
    result = await BacktraderEngine(execution_config=cfg).run(_BUY_HOLD, bars)
    assert result.engine == "backtrader"
    assert len(result.trades) >= 1
    # Fees should be positive
    assert result.trades[0]["fees"] > 0


@pytest.mark.asyncio
async def test_accepts_tiered_commission():
    bars = _make_bars(100)
    cfg = ExecutionConfig(
        commission=TieredCommission(tiers=[(0, 100, 0.001), (100, None, 0.0005)]),
        slippage=FixedBpsSlippage(bps=0),
        fill=NextBarOpenFill(),
    )
    result = await BacktraderEngine(execution_config=cfg).run(_BUY_HOLD, bars)
    assert result.engine == "backtrader"


@pytest.mark.asyncio
async def test_accepts_a_share_commission():
    bars = _make_bars(100)
    cfg = ExecutionConfig(
        commission=AShareCommission(base_rate=0.00025, stamp_rate=0.001),
        slippage=FixedBpsSlippage(bps=2),
        fill=NextBarOpenFill(),
    )
    result = await BacktraderEngine(execution_config=cfg).run(_BUY_HOLD, bars)
    assert result.engine == "backtrader"
    assert len(result.trades) >= 1
    # Total fees should be positive
    assert result.trades[0]["fees"] > 0


# ── Registry wiring ───────────────────────────────────────────────────────────

def test_registry_returns_backtrader_for_stock():
    from services.engines.registry import get_engine
    engine = get_engine("stock")
    assert isinstance(engine, BacktraderEngine)
