"""
Extended metrics tests — Task 2.

All assertions are hand-computed from first principles.
Covers the new MetricsOut v2 fields and the new TradeOut v2 fields.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from services.metrics import compute_metrics


# ── Helper ────────────────────────────────────────────────────────────────────

def _equity_from_returns(returns: list[float], start: float = 100_000.0) -> pd.Series:
    arr = np.array(returns)
    values = start * np.cumprod(np.append([1.0], 1 + arr))
    return pd.Series(values, index=pd.date_range("2023-01-01", periods=len(values), freq="D"))


def _trades(*pnls: float, bars_held: int = 5) -> list[dict]:
    return [{"pnl": p, "fees": 0.0, "slippage_cost": 0.0, "bars_held": bars_held} for p in pnls]


# ── Returns group ─────────────────────────────────────────────────────────────

class TestTotalReturn:
    def test_positive(self):
        equity = pd.Series([100_000.0, 120_000.0])
        m = compute_metrics(equity, [])
        assert m["total_return"] == pytest.approx(0.20)

    def test_negative(self):
        equity = pd.Series([100_000.0, 80_000.0])
        m = compute_metrics(equity, [])
        assert m["total_return"] == pytest.approx(-0.20)

    def test_flat(self):
        equity = pd.Series([100_000.0, 100_000.0, 100_000.0])
        m = compute_metrics(equity, [])
        assert m["total_return"] == pytest.approx(0.0)


# ── Risk group ────────────────────────────────────────────────────────────────

class TestVolatility:
    def test_zero_for_constant_returns(self):
        # Constant 1% returns → std = 0 → vol = 0
        equity = _equity_from_returns([0.01] * 50)
        m = compute_metrics(equity, [], bars_per_year=252)
        assert m["volatility"] == pytest.approx(0.0, abs=1e-9)

    def test_annualized_formula(self):
        # Alternating ±2% returns → std = 0.02, annualized = 0.02 * sqrt(252)
        returns = [0.02, -0.02] * 25
        equity = _equity_from_returns(returns)
        m = compute_metrics(equity, [], bars_per_year=252)
        expected = 0.02 * np.sqrt(252)
        assert m["volatility"] == pytest.approx(expected, rel=1e-3)


class TestDownsideVolatility:
    def test_only_counts_negative_returns(self):
        # One positive, one negative return: downside vol only uses negative
        returns = [0.05, -0.03]
        equity = _equity_from_returns(returns)
        m = compute_metrics(equity, [], bars_per_year=252)
        # downside returns = [-0.03], std of single value = 0 → None
        assert m["downside_volatility"] is None

    def test_non_zero_with_multiple_negatives(self):
        returns = [0.01, -0.02, 0.03, -0.04, -0.01]
        equity = _equity_from_returns(returns)
        m = compute_metrics(equity, [], bars_per_year=252)
        neg = np.array([-0.02, -0.04, -0.01])
        expected = float(neg.std(ddof=1) * np.sqrt(252))
        assert m["downside_volatility"] == pytest.approx(expected, rel=1e-3)


class TestVaR95:
    def test_known_distribution(self):
        # 20 returns: 19 × 0.01, 1 × -0.10
        # 5th percentile of 20 = np.percentile(returns, 5)
        returns = [0.01] * 19 + [-0.10]
        equity = _equity_from_returns(returns)
        m = compute_metrics(equity, [])
        r = np.array(returns)
        expected_var = float(-np.percentile(r, 5))
        assert m["var_95"] == pytest.approx(expected_var, rel=1e-4)

    def test_is_positive(self):
        # var_95 is a loss magnitude — must be positive for typical distributions
        rng = np.random.default_rng(7)
        equity = _equity_from_returns(rng.normal(0.001, 0.02, 500).tolist())
        m = compute_metrics(equity, [])
        assert m["var_95"] is not None
        assert m["var_95"] > 0


class TestCVaR95:
    def test_known_values(self):
        # returns where worst 5% is exactly -0.10
        returns = [0.01] * 19 + [-0.10]
        equity = _equity_from_returns(returns)
        m = compute_metrics(equity, [])
        r = np.array(returns)
        threshold = np.percentile(r, 5)
        expected_cvar = float(-r[r <= threshold].mean())
        assert m["cvar_95"] == pytest.approx(expected_cvar, rel=1e-4)

    def test_cvar_ge_var(self):
        # CVaR is always >= VaR by definition
        rng = np.random.default_rng(13)
        equity = _equity_from_returns(rng.normal(0.001, 0.02, 500).tolist())
        m = compute_metrics(equity, [])
        assert m["cvar_95"] >= m["var_95"] - 1e-9


class TestMaxDrawdownDuration:
    def test_simple_drawdown(self):
        # Peak 100k → drops → recovers: 3 bars in drawdown
        equity = pd.Series([100_000, 105_000, 90_000, 92_000, 95_000, 106_000])
        m = compute_metrics(equity, [])
        # Bars 2, 3, 4 are below peak of 105_000 → 3-bar drawdown
        assert m["max_drawdown_duration_days"] == 3

    def test_no_drawdown(self):
        equity = pd.Series([100_000, 101_000, 102_000, 103_000])
        m = compute_metrics(equity, [])
        assert m["max_drawdown_duration_days"] == 0


# ── Risk-adjusted group ───────────────────────────────────────────────────────

class TestCalmarRatio:
    def test_known_values(self):
        # Build equity with known cagr and drawdown
        # Use 252 bars (1 year), starts 100k, ends 110k, dips to 90k in between
        n = 252
        vals = [100_000] + [95_000] * 10 + [90_000] + [100_000] * 50 + [110_000] * (n - 62)
        equity = pd.Series(vals, index=pd.date_range("2023-01-01", periods=n, freq="D"))
        m = compute_metrics(equity, [], bars_per_year=252)
        assert m["calmar_ratio"] is not None
        # calmar = cagr / abs(max_drawdown)
        assert m["calmar_ratio"] == pytest.approx(
            m["cagr"] / abs(m["max_drawdown"]), rel=1e-3
        )

    def test_none_when_no_drawdown(self):
        # Perfectly flat equity → max_drawdown = 0 → calmar = None
        equity = pd.Series([100_000.0] * 50)
        m = compute_metrics(equity, [])
        assert m["calmar_ratio"] is None


class TestOmegaRatio:
    def test_known_values(self):
        # returns: [+0.01, +0.02, -0.005, -0.003]
        # positive sum = 0.03, negative sum abs = 0.008
        # omega = 0.03 / 0.008 = 3.75
        equity = _equity_from_returns([0.01, 0.02, -0.005, -0.003])
        m = compute_metrics(equity, [])
        assert m["omega_ratio"] == pytest.approx(3.75, rel=1e-3)

    def test_none_when_no_negative_returns(self):
        equity = _equity_from_returns([0.01, 0.02, 0.005])
        m = compute_metrics(equity, [])
        assert m["omega_ratio"] is None


class TestTailRatio:
    def test_symmetric_returns(self):
        # Symmetric distribution → tail ratio ≈ 1.0
        returns = list(np.linspace(-0.10, 0.10, 101))
        equity = _equity_from_returns(returns)
        m = compute_metrics(equity, [])
        # p95 ≈ 0.09, p05 ≈ -0.09 → ratio ≈ 1.0
        assert m["tail_ratio"] == pytest.approx(1.0, rel=0.05)

    def test_positive_skew_above_one(self):
        # Right-skewed: more upside → tail_ratio > 1
        returns = [0.001] * 90 + [0.10] * 5 + [-0.02] * 5
        equity = _equity_from_returns(returns)
        m = compute_metrics(equity, [])
        assert m["tail_ratio"] is not None
        assert m["tail_ratio"] > 1.0


# ── Trade quality group ───────────────────────────────────────────────────────

class TestAvgWinLoss:
    def test_known_values(self):
        trades = _trades(100.0, 200.0, -50.0, -75.0)
        equity = pd.Series([100_000] * 5)
        m = compute_metrics(equity, trades)
        assert m["avg_win"]  == pytest.approx(150.0)
        assert m["avg_loss"] == pytest.approx(62.5)

    def test_none_when_no_winners(self):
        trades = _trades(-100.0, -50.0)
        equity = pd.Series([100_000] * 3)
        m = compute_metrics(equity, trades)
        assert m["avg_win"] is None

    def test_none_when_no_losers(self):
        trades = _trades(100.0, 50.0)
        equity = pd.Series([100_000] * 3)
        m = compute_metrics(equity, trades)
        assert m["avg_loss"] is None


class TestLargestWinLoss:
    def test_known_values(self):
        trades = _trades(100.0, 200.0, -50.0, -75.0)
        equity = pd.Series([100_000] * 5)
        m = compute_metrics(equity, trades)
        assert m["largest_win"]  == pytest.approx(200.0)
        assert m["largest_loss"] == pytest.approx(-75.0)


class TestAvgTradeDurationBars:
    def test_known_value(self):
        # 3 trades with bars_held 5, 10, 15 → avg = 10
        trades = [
            {"pnl": 100.0, "fees": 0.0, "slippage_cost": 0.0, "bars_held": 5},
            {"pnl": -50.0, "fees": 0.0, "slippage_cost": 0.0, "bars_held": 10},
            {"pnl": 200.0, "fees": 0.0, "slippage_cost": 0.0, "bars_held": 15},
        ]
        equity = pd.Series([100_000] * 4)
        m = compute_metrics(equity, trades)
        assert m["avg_trade_duration_bars"] == pytest.approx(10.0)

    def test_none_when_no_trades(self):
        equity = pd.Series([100_000] * 10)
        m = compute_metrics(equity, [])
        assert m["avg_trade_duration_bars"] is None


# ── Exposure and turnover ─────────────────────────────────────────────────────

class TestExposurePct:
    def test_known_value(self):
        # 2 trades of 5 bars each, equity has 20 bars → exposure = 10/20 = 0.5
        trades = [
            {"pnl": 100.0, "fees": 0.0, "slippage_cost": 0.0, "bars_held": 5},
            {"pnl":  50.0, "fees": 0.0, "slippage_cost": 0.0, "bars_held": 5},
        ]
        equity = pd.Series([100_000.0] * 20)
        m = compute_metrics(equity, trades)
        assert m["exposure_pct"] == pytest.approx(0.5)

    def test_zero_when_no_trades(self):
        equity = pd.Series([100_000.0] * 20)
        m = compute_metrics(equity, [])
        assert m["exposure_pct"] == pytest.approx(0.0)


class TestTurnover:
    def test_known_value(self):
        # 2 trades, 20 bars → turnover = 2*2/20 = 0.2
        trades = _trades(100.0, 50.0)
        equity = pd.Series([100_000.0] * 20)
        m = compute_metrics(equity, trades)
        assert m["turnover"] == pytest.approx(0.2)


# ── Schema version ────────────────────────────────────────────────────────────

class TestSchemaVersion:
    def test_metrics_schema_version_is_2(self):
        equity = pd.Series([100_000.0, 101_000.0])
        m = compute_metrics(equity, [])
        assert m["schema_version"] == 2


# ── New TradeOut fields from _simulate ───────────────────────────────────────

def _make_df_known(closes: list[float]) -> pd.DataFrame:
    n = len(closes)
    closes_arr = np.array(closes, dtype=float)
    return pd.DataFrame(
        {
            "open":   closes_arr,
            "high":   closes_arr * 1.005,
            "low":    closes_arr * 0.995,
            "close":  closes_arr,
            "volume": [1000.0] * n,
        },
        index=pd.date_range("2023-01-01", periods=n, freq="D"),
    )


class TestTradeNewFields:
    """Verify _simulate records all new TradeOut v2 fields."""

    @pytest.fixture
    def trade(self):
        """
        Known setup:
          - entry signal at bar 1 → fills at close[2] = 100.0  (CurrentCloseDelayedFill)
          - close[3] = 90  (price dip  → MAE candidate)
          - close[4] = 120 (price peak → MFE candidate)
          - exit signal at bar 4 → fills at close[5] = 115.0
          bars_held = 5 - 2 = 3
          MAE = (90 - 100) / 100 = -0.10
          MFE = (120 - 100) / 100 = 0.20
        """
        from services.engines._runtime import run_strategy
        from services.engines.execution_model import (
            CurrentCloseDelayedFill, ExecutionConfig, FixedBpsSlippage, PercentageCommission
        )

        closes = [95.0, 98.0, 100.0, 90.0, 120.0, 115.0, 110.0, 108.0]
        df = _make_df_known(closes)

        # entries[1]=True → fills at bar 2 (close=100)
        # exits[4]=True → fills at bar 5 (close=115)
        code = """\
import pandas as pd
def run(ohlcv):
    n = len(ohlcv)
    entries = pd.Series(False, index=ohlcv.index)
    exits   = pd.Series(False, index=ohlcv.index)
    entries.iloc[1] = True
    exits.iloc[4]   = True
    return {"entries": entries, "exits": exits}
"""
        cfg = ExecutionConfig(
            commission=PercentageCommission(rate=0.0),
            slippage=FixedBpsSlippage(bps=0),
            fill=CurrentCloseDelayedFill(latency_bars=1),
        )
        _, trades, _ = run_strategy(code, df, execution_config=cfg)
        assert len(trades) == 1
        return trades[0]

    def test_has_entry_time(self, trade):
        assert "entry_time" in trade
        assert isinstance(trade["entry_time"], str)

    def test_has_exit_time(self, trade):
        assert "exit_time" in trade
        assert isinstance(trade["exit_time"], str)
        assert trade["exit_time"] > trade["entry_time"]

    def test_has_quantity(self, trade):
        assert "quantity" in trade
        assert trade["quantity"] > 0

    def test_has_pnl_pct(self, trade):
        # 0 commission, fill at 100 then 115 → pnl_pct = 15/100 = 0.15
        assert "pnl_pct" in trade
        assert trade["pnl_pct"] == pytest.approx(0.15, rel=1e-3)

    def test_has_bars_held(self, trade):
        # entry bar 2, exit bar 5 → bars_held = 3
        assert "bars_held" in trade
        assert trade["bars_held"] == 3

    def test_mae_correct(self, trade):
        # min close during trade = 90, entry = 100 → MAE = -0.10
        assert "mae" in trade
        assert trade["mae"] == pytest.approx(-0.10, rel=1e-3)

    def test_mfe_correct(self, trade):
        # max close during trade = 120, entry = 100 → MFE = 0.20
        assert "mfe" in trade
        assert trade["mfe"] == pytest.approx(0.20, rel=1e-3)
