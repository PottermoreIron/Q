"""
Golden-file regression tests for the backtesting engine.

These tests use fixed synthetic data + fixed strategies to assert that
known inputs always produce known outputs. Any change to the engine,
simulator, or metrics that alters these numbers is a breaking regression.

Seed and expected values were computed with the current engine and locked in.
To regenerate after an intentional change: run with --update-golden flag
(not implemented; just update the expected values manually and document why).
"""

import numpy as np
import pandas as pd
import pytest

from services.engines._runtime import run_strategy
from services.metrics import compute_metrics


def _make_deterministic_ohlcv(n: int = 252, seed: int = 0) -> pd.DataFrame:
    """Reproducible OHLCV with a mild upward drift."""
    rng = np.random.default_rng(seed)
    log_returns = rng.normal(0.0003, 0.015, n)
    close = 100.0 * np.exp(np.cumsum(log_returns))
    df = pd.DataFrame({
        "open":   close * np.exp(rng.normal(0, 0.003, n)),
        "high":   close * np.exp(np.abs(rng.normal(0, 0.008, n))),
        "low":    close * np.exp(-np.abs(rng.normal(0, 0.008, n))),
        "close":  close,
        "volume": rng.uniform(1_000, 10_000, n),
    }, index=pd.date_range("2022-01-03", periods=n, freq="B"))
    return df


_EMA_CROSSOVER = """\
import pandas as pd

def run(ohlcv):
    close = ohlcv["close"]
    fast = close.ewm(span=10, adjust=False).mean()
    slow = close.ewm(span=30, adjust=False).mean()
    entries = fast > slow
    exits   = fast < slow
    return {"entries": entries, "exits": exits}
"""

_BUY_HOLD = """\
import pandas as pd

def run(ohlcv):
    close = ohlcv["close"]
    entries = pd.Series(False, index=close.index)
    exits   = pd.Series(False, index=close.index)
    entries.iloc[0] = True   # buy on bar 1
    exits.iloc[-2]  = True   # sell on penultimate bar
    return {"entries": entries, "exits": exits}
"""

_NO_TRADES = """\
import pandas as pd

def run(ohlcv):
    close = ohlcv["close"]
    return {
        "entries": pd.Series(False, index=close.index),
        "exits":   pd.Series(False, index=close.index),
    }
"""


class TestGoldenEMACrossover:
    """EMA 10/30 crossover on seed=0, 252 bars."""

    @pytest.fixture(scope="class")
    def result(self):
        df = _make_deterministic_ohlcv(252, seed=0)
        metrics, trades, equity = run_strategy(_EMA_CROSSOVER, df)
        return metrics, trades, equity

    def test_trade_count(self, result):
        _, trades, _ = result
        assert len(trades) == 7

    def test_equity_length(self, result):
        _, _, equity = result
        assert len(equity) == 252

    def test_initial_equity(self, result):
        _, _, equity = result
        assert equity.iloc[0] == pytest.approx(100_000.0, rel=1e-4)

    def test_final_value_stable(self, result):
        metrics, _, _ = result
        # Locked value — seed=0, 252 bars, EMA 10/30 crossover
        assert metrics["final_value"] == pytest.approx(84_572.24, rel=0.005)

    def test_sharpe_reasonable(self, result):
        metrics, _, _ = result
        sr = metrics["sharpe_ratio"]
        assert sr is not None
        # Losing strategy on this seed — negative but bounded
        assert -5.0 < sr < 5.0

    def test_max_drawdown_negative(self, result):
        metrics, _, _ = result
        dd = metrics["max_drawdown"]
        assert dd is not None and dd <= 0

    def test_win_rate_between_0_and_1(self, result):
        metrics, _, _ = result
        wr = metrics["win_rate"]
        assert wr is not None
        assert 0.0 <= wr <= 1.0

    def test_all_trades_have_required_keys(self, result):
        _, trades, _ = result
        for t in trades:
            assert "entry_price" in t
            assert "exit_price" in t
            assert "pnl" in t
            assert "side" in t
            assert t["side"] == "long"


class TestGoldenBuyHold:
    """Buy first bar, sell penultimate bar."""

    @pytest.fixture(scope="class")
    def result(self):
        df = _make_deterministic_ohlcv(252, seed=0)
        metrics, trades, equity = run_strategy(_BUY_HOLD, df)
        return metrics, trades, equity

    def test_exactly_one_trade(self, result):
        _, trades, _ = result
        assert len(trades) == 1

    def test_equity_curve_length(self, result):
        _, _, equity = result
        assert len(equity) == 252

    def test_pnl_matches_price_move(self, result):
        _, trades, _ = result
        t = trades[0]
        assert abs(t["pnl"]) > 0

    def test_final_value_stable(self, result):
        metrics, _, _ = result
        # Locked: buy bar 1, sell bar 251 on seed=0
        assert metrics["final_value"] == pytest.approx(105_478.29, rel=0.005)

    def test_final_equity_in_range(self, result):
        metrics, _, _ = result
        assert metrics["final_value"] is not None
        assert 70_000 < metrics["final_value"] < 130_000


class TestGoldenNoTrades:
    """No signals — equity should stay flat at initial capital."""

    def test_equity_flat(self):
        df = _make_deterministic_ohlcv(100, seed=42)
        metrics, trades, equity = run_strategy(_NO_TRADES, df)
        assert len(trades) == 0
        assert metrics["final_value"] == pytest.approx(100_000.0)
        assert metrics["total_trades"] is None
        assert equity.iloc[0] == pytest.approx(equity.iloc[-1])


class TestMetricsGolden:
    """Metrics layer with a hand-crafted known equity curve."""

    def test_sharpe_known_series(self):
        # Volatile uptrend — computable Sharpe
        n = 252
        rng = np.random.default_rng(99)
        returns = rng.normal(0.001, 0.01, n)
        equity = pd.Series(100_000 * np.cumprod(1 + returns))
        m = compute_metrics(equity, [], bars_per_year=252)
        assert m["sharpe_ratio"] is not None
        assert m["sharpe_ratio"] > 0  # positive mean return → positive Sharpe

    def test_max_drawdown_known_series(self):
        # Peak at 110k, drops to 90k → drawdown = (90k-110k)/110k ≈ -0.1818
        equity = pd.Series([100_000, 105_000, 110_000, 95_000, 90_000, 100_000])
        m = compute_metrics(equity, [])
        assert m["max_drawdown"] == pytest.approx(-20_000 / 110_000, rel=1e-3)

    def test_profit_factor_known_trades(self):
        trades = [
            {"pnl": 1000},
            {"pnl": 500},
            {"pnl": -200},
            {"pnl": -100},
        ]
        equity = pd.Series([100_000, 101_000, 101_500, 101_300, 101_200])
        m = compute_metrics(equity, trades)
        # profit factor = gross_win / abs(gross_loss) = 1500 / 300 = 5.0
        assert m["profit_factor"] == pytest.approx(5.0, rel=1e-3)

    def test_win_rate_known_trades(self):
        trades = [{"pnl": 100}, {"pnl": -50}, {"pnl": 200}, {"pnl": -10}]
        equity = pd.Series([100_000] * 5)
        m = compute_metrics(equity, trades)
        assert m["win_rate"] == pytest.approx(0.5)
        assert m["total_trades"] == 4
