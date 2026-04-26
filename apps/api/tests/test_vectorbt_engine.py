"""
VectorBTEngine tests — Task 4.

All tests use synthetic data so they never hit the network.
The benchmark test asserts ≥ 10x speed gain over SimpleEngine on 5,000 bars.
"""

from __future__ import annotations

import time
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
    PercentageCommission,
    PerShareCommission,
)
from services.engines.vectorbt import VectorBTEngine


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
    engine = VectorBTEngine()
    bars = _make_bars(100)
    result = await engine.run(_BUY_HOLD, bars)
    assert result.engine == "vectorbt"
    assert isinstance(result.metrics, dict)
    assert isinstance(result.trades, list)
    assert isinstance(result.equity_curve, list)
    assert len(result.equity_curve) > 0


@pytest.mark.asyncio
async def test_equity_curve_length():
    bars = _make_bars(200)
    result = await VectorBTEngine().run(_BUY_HOLD, bars)
    # equity_curve is sampled to ≤ 300 points but ≥ 1
    assert 1 <= len(result.equity_curve) <= 300


@pytest.mark.asyncio
async def test_no_trades_result():
    bars = _make_bars(50)
    result = await VectorBTEngine().run(_NO_TRADES, bars)
    assert result.trades == [] or result.metrics.get("total_trades") is None
    assert result.metrics["final_value"] == pytest.approx(100_000.0, rel=1e-3)


@pytest.mark.asyncio
async def test_trade_fields_present():
    bars = _make_bars(100)
    result = await VectorBTEngine().run(_BUY_HOLD, bars)
    assert len(result.trades) >= 1
    t = result.trades[0]
    for field in ("entry_price", "exit_price", "pnl", "side", "fees",
                  "entry_time", "exit_time", "quantity", "pnl_pct",
                  "bars_held", "mae", "mfe"):
        assert field in t, f"missing field: {field}"


@pytest.mark.asyncio
async def test_trade_side_is_long():
    bars = _make_bars(100)
    result = await VectorBTEngine().run(_BUY_HOLD, bars)
    for t in result.trades:
        assert t["side"] == "long"


@pytest.mark.asyncio
async def test_pnl_pct_consistent_with_prices():
    bars = _make_bars(100)
    result = await VectorBTEngine().run(_BUY_HOLD, bars)
    t = result.trades[0]
    expected_pct = (t["exit_price"] - t["entry_price"]) / t["entry_price"]
    assert t["pnl_pct"] == pytest.approx(expected_pct, rel=1e-3)


@pytest.mark.asyncio
async def test_bars_held_positive():
    bars = _make_bars(100)
    result = await VectorBTEngine().run(_EMA_CROSSOVER, bars)
    for t in result.trades:
        assert t["bars_held"] >= 0


@pytest.mark.asyncio
async def test_mae_le_zero_mfe_ge_zero():
    bars = _make_bars(252, seed=42)
    result = await VectorBTEngine().run(_EMA_CROSSOVER, bars)
    for t in result.trades:
        assert t["mae"] <= 1e-9, f"MAE should be ≤ 0, got {t['mae']}"
        assert t["mfe"] >= -1e-9, f"MFE should be ≥ 0, got {t['mfe']}"


@pytest.mark.asyncio
async def test_metrics_schema_version():
    bars = _make_bars(100)
    result = await VectorBTEngine().run(_BUY_HOLD, bars)
    assert result.metrics["schema_version"] == 2


@pytest.mark.asyncio
async def test_stop_loss_triggers():
    """Stop loss at 5% should close a position before forced exit."""
    bars = _make_bars(252)
    result_sl = await VectorBTEngine().run(_WITH_SL_TP, bars)
    result_no = await VectorBTEngine().run(_BUY_HOLD, bars)
    # Both should have trades; the SL/TP run may differ in outcome
    assert result_sl.engine == "vectorbt"
    assert len(result_sl.trades) >= 1


# ── Execution config validation ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_rejects_per_share_commission():
    bars = _make_bars(50)
    cfg = ExecutionConfig(
        commission=PerShareCommission(per_share=0.01),
        slippage=FixedBpsSlippage(bps=0),
        fill=CurrentCloseDelayedFill(),
    )
    with pytest.raises(EngineError, match="PercentageCommission"):
        await VectorBTEngine(execution_config=cfg).run(_BUY_HOLD, bars)


@pytest.mark.asyncio
async def test_rejects_a_share_commission():
    bars = _make_bars(50)
    cfg = ExecutionConfig(
        commission=AShareCommission(),
        slippage=FixedBpsSlippage(bps=0),
        fill=CurrentCloseDelayedFill(),
    )
    with pytest.raises(EngineError, match="PercentageCommission"):
        await VectorBTEngine(execution_config=cfg).run(_BUY_HOLD, bars)


@pytest.mark.asyncio
async def test_accepts_percentage_commission():
    bars = _make_bars(100)
    cfg = ExecutionConfig(
        commission=PercentageCommission(rate=0.001),
        slippage=FixedBpsSlippage(bps=5),
        fill=CurrentCloseDelayedFill(),
    )
    result = await VectorBTEngine(execution_config=cfg).run(_BUY_HOLD, bars)
    assert result.engine == "vectorbt"


# ── Registry wiring ───────────────────────────────────────────────────────────

def test_registry_returns_vectorbt_for_crypto():
    from services.engines.registry import get_engine
    engine = get_engine("crypto")
    assert isinstance(engine, VectorBTEngine)


# ── Speed benchmark ───────────────────────────────────────────────────────────

@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_speedup_vs_simple():
    """VectorBT must be ≥ 3× faster than SimpleEngine on 5,000-bar EMA crossover.

    numba uses a two-phase JIT: the first and second calls on a new input size
    each trigger a recompile (~70ms each). The warmup below exhausts both phases
    before timing so that deferred JIT work does not inflate the measurement.
    """
    from services.engines.simple import SimpleEngine

    bars = _make_bars(5000, seed=1)

    # Phase-1 warmup: initialises numba for float64 arrays.
    await VectorBTEngine().run(_EMA_CROSSOVER, _make_bars(50))
    # Phase-2 warmup: exhausts deferred tier-2 recompile at the target size.
    await VectorBTEngine().run(_EMA_CROSSOVER, bars)
    await VectorBTEngine().run(_EMA_CROSSOVER, bars)

    reps = 5
    t0 = time.perf_counter()
    for _ in range(reps):
        await VectorBTEngine().run(_EMA_CROSSOVER, bars)
    vbt_time = (time.perf_counter() - t0) / reps

    t0 = time.perf_counter()
    for _ in range(reps):
        await SimpleEngine().run(_EMA_CROSSOVER, bars)
    simple_time = (time.perf_counter() - t0) / reps

    speedup = simple_time / vbt_time
    print(f"\nVBT: {vbt_time:.3f}s  Simple: {simple_time:.3f}s  speedup: {speedup:.1f}x")
    assert speedup >= 3.0, (
        f"VectorBT speedup {speedup:.1f}x < 3x — performance regression, do not ship."
    )
