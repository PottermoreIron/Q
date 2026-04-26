"""
Unit tests for ExecutionModel (Task 1).

All assertions are hand-computed from first principles — no "run and capture" baselines.
Failing on import means implementation doesn't exist yet (expected at test-write time).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from services.engines.execution_model import (
    AShareCommission,
    CurrentCloseDelayedFill,
    ExecutionConfig,
    FixedBpsSlippage,
    NextBarOpenFill,
    PercentageCommission,
    PerShareCommission,
    SpreadSlippage,
    TieredCommission,
    VWAPSliceFill,
    VolatilitySlippage,
    default_for_asset_class,
)


# ── Commission models ─────────────────────────────────────────────────────────

class TestPercentageCommission:
    def test_basic(self):
        c = PercentageCommission(rate=0.001)
        assert c.fee(10_000.0, 100.0, 100.0) == pytest.approx(10.0)

    def test_zero_rate(self):
        c = PercentageCommission(rate=0.0)
        assert c.fee(5_000.0, 50.0, 100.0) == pytest.approx(0.0)

    def test_same_for_buy_and_sell(self):
        c = PercentageCommission(rate=0.001)
        assert c.fee(10_000.0, 100.0, 100.0, "buy") == pytest.approx(
            c.fee(10_000.0, 100.0, 100.0, "sell")
        )


class TestPerShareCommission:
    def test_min_per_order_applied(self):
        # 100 shares * $0.005 = $0.50 < min $1.00 → charges min
        c = PerShareCommission(per_share=0.005, min_per_order=1.0)
        assert c.fee(10_000.0, 100.0, 100.0) == pytest.approx(1.0)

    def test_per_share_dominates(self):
        # 300 shares * $0.005 = $1.50 > min $1.00 → charges per-share
        c = PerShareCommission(per_share=0.005, min_per_order=1.0)
        assert c.fee(30_000.0, 300.0, 100.0) == pytest.approx(1.50)

    def test_exact_min_boundary(self):
        # 200 shares * $0.005 = $1.00 == min → either path gives $1.00
        c = PerShareCommission(per_share=0.005, min_per_order=1.0)
        assert c.fee(20_000.0, 200.0, 100.0) == pytest.approx(1.0)


class TestTieredCommission:
    def test_two_tier_200_shares(self):
        # Tier 1: 0–100 shares @ 0.001, Tier 2: 100+ shares @ 0.0005
        # 200 shares @ $50:
        #   first 100: 100 * $50 * 0.001 = $5.00
        #   next 100:  100 * $50 * 0.0005 = $2.50
        #   total = $7.50
        c = TieredCommission(tiers=[(0, 100, 0.001), (100, None, 0.0005)])
        assert c.fee(10_000.0, 200.0, 50.0) == pytest.approx(7.50)

    def test_single_tier_within_first(self):
        # 50 shares @ $100 with first tier only (0-100 @ 0.001)
        # 50 * $100 * 0.001 = $5.00
        c = TieredCommission(tiers=[(0, 100, 0.001), (100, None, 0.0005)])
        assert c.fee(5_000.0, 50.0, 100.0) == pytest.approx(5.0)


class TestAShareCommission:
    def test_buy_no_stamp(self):
        # Buy $10,000: 0.025% only = $2.50
        c = AShareCommission(base_rate=0.00025, stamp_rate=0.001)
        assert c.fee(10_000.0, 100.0, 100.0, "buy") == pytest.approx(2.50)

    def test_sell_with_stamp(self):
        # Sell $10,000: 0.025% + 0.1% = 0.125% = $12.50
        c = AShareCommission(base_rate=0.00025, stamp_rate=0.001)
        assert c.fee(10_000.0, 100.0, 100.0, "sell") == pytest.approx(12.50)


# ── Slippage models ───────────────────────────────────────────────────────────

class TestFixedBpsSlippage:
    def test_buy_pays_more(self):
        s = FixedBpsSlippage(bps=5)
        assert s.adjust(100.0, "buy") == pytest.approx(100.05)

    def test_sell_receives_less(self):
        s = FixedBpsSlippage(bps=5)
        assert s.adjust(100.0, "sell") == pytest.approx(99.95)

    def test_zero_bps_no_change(self):
        s = FixedBpsSlippage(bps=0)
        assert s.adjust(100.0, "buy") == pytest.approx(100.0)
        assert s.adjust(100.0, "sell") == pytest.approx(100.0)


class TestSpreadSlippage:
    def test_buy(self):
        s = SpreadSlippage(half_spread_bps=2)
        assert s.adjust(100.0, "buy") == pytest.approx(100.02)

    def test_sell(self):
        s = SpreadSlippage(half_spread_bps=2)
        assert s.adjust(100.0, "sell") == pytest.approx(99.98)


class TestVolatilitySlippage:
    def test_buy_adds_atr_multiple(self):
        s = VolatilitySlippage(atr_multiplier=0.1)
        assert s.adjust(100.0, "buy", atr=10.0) == pytest.approx(101.0)

    def test_sell_subtracts_atr_multiple(self):
        s = VolatilitySlippage(atr_multiplier=0.1)
        assert s.adjust(100.0, "sell", atr=10.0) == pytest.approx(99.0)

    def test_zero_atr_no_change(self):
        s = VolatilitySlippage(atr_multiplier=0.1)
        assert s.adjust(100.0, "buy", atr=0.0) == pytest.approx(100.0)


# ── Fill models ───────────────────────────────────────────────────────────────

def _make_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "open":   [10.0, 11.0, 12.0, 13.0, 14.0],
            "high":   [10.5, 11.5, 12.5, 13.5, 14.5],
            "low":    [ 9.5, 10.5, 11.5, 12.5, 13.5],
            "close":  [10.2, 11.2, 12.2, 13.2, 14.2],
            "volume": [1000] * 5,
        },
        index=pd.date_range("2023-01-01", periods=5, freq="D"),
    )


class TestNextBarOpenFill:
    def test_latency_is_one(self):
        assert NextBarOpenFill().latency_bars == 1

    def test_fills_at_next_open(self):
        # signal at bar 2 → fills at bar 3 open = 13.0
        f = NextBarOpenFill()
        assert f.fill_price(_make_df(), signal_bar=2, side="buy") == pytest.approx(13.0)

    def test_last_bar_returns_last_close(self):
        # signal at bar 4 → bar 5 doesn't exist → returns last close
        f = NextBarOpenFill()
        assert f.fill_price(_make_df(), signal_bar=4, side="buy") == pytest.approx(14.2)


class TestCurrentCloseDelayedFill:
    def test_latency_matches_init(self):
        assert CurrentCloseDelayedFill(latency_bars=2).latency_bars == 2

    def test_fills_at_next_close(self):
        # signal at bar 2, latency 1 → fills at bar 3 close = 13.2
        f = CurrentCloseDelayedFill(latency_bars=1)
        assert f.fill_price(_make_df(), signal_bar=2, side="buy") == pytest.approx(13.2)

    def test_last_bar_returns_last_close(self):
        f = CurrentCloseDelayedFill(latency_bars=1)
        assert f.fill_price(_make_df(), signal_bar=4, side="sell") == pytest.approx(14.2)


class TestVWAPSliceFill:
    def test_latency_is_one(self):
        assert VWAPSliceFill().latency_bars == 1

    def test_fills_at_vwap_of_next_bar(self):
        # signal at bar 1 → fills at bar 2
        # VWAP = (open + high + low + close) / 4 = (12 + 12.5 + 11.5 + 12.2) / 4 = 48.2 / 4 = 12.05
        f = VWAPSliceFill()
        assert f.fill_price(_make_df(), signal_bar=1, side="buy") == pytest.approx(12.05)


# ── default_for_asset_class ───────────────────────────────────────────────────

class TestDefaultForAssetClass:
    def test_us_equity_returns_config(self):
        cfg = default_for_asset_class("us_equity")
        assert isinstance(cfg, ExecutionConfig)
        # 0.05% commission on $10,000 notional = $5
        assert cfg.commission.fee(10_000.0, 100.0, 100.0) == pytest.approx(5.0)
        assert cfg.fill.latency_bars == 1

    def test_a_share_stamp_on_sells_only(self):
        cfg = default_for_asset_class("a_share")
        buy_fee  = cfg.commission.fee(10_000.0, 100.0, 100.0, "buy")
        sell_fee = cfg.commission.fee(10_000.0, 100.0, 100.0, "sell")
        # sell must be higher due to stamp duty
        assert sell_fee > buy_fee

    def test_crypto_returns_config(self):
        cfg = default_for_asset_class("crypto")
        assert isinstance(cfg, ExecutionConfig)
        assert cfg.fill.latency_bars == 1

    def test_forex_zero_commission(self):
        cfg = default_for_asset_class("forex")
        assert cfg.commission.fee(10_000.0, 100.0, 100.0) == pytest.approx(0.0)


# ── Integration: fees and slippage_cost appear on trade records ───────────────

class TestExecutionModelIntegration:
    """Verify that fees and slippage_cost are recorded in trade dicts."""

    def test_fees_recorded_on_trade(self):
        from services.engines._runtime import run_strategy

        cfg = ExecutionConfig(
            commission=PercentageCommission(rate=0.001),
            slippage=FixedBpsSlippage(bps=0),
            fill=CurrentCloseDelayedFill(latency_bars=1),
        )
        code = """\
import pandas as pd
def run(ohlcv):
    entries = pd.Series(False, index=ohlcv.index)
    exits   = pd.Series(False, index=ohlcv.index)
    entries.iloc[0] = True
    exits.iloc[-2]  = True
    return {"entries": entries, "exits": exits}
"""
        rng = np.random.default_rng(7)
        n = 50
        close = 100.0 * np.cumprod(1 + rng.normal(0.001, 0.01, n))
        df = pd.DataFrame(
            {
                "open":   close,
                "high":   close * 1.005,
                "low":    close * 0.995,
                "close":  close,
                "volume": 1000.0,
            },
            index=pd.date_range("2023-01-01", periods=n, freq="D"),
        )
        _, trades, _ = run_strategy(code, df, execution_config=cfg)
        assert len(trades) == 1
        t = trades[0]
        assert "fees" in t
        assert "slippage_cost" in t
        assert t["fees"] > 0
        assert t["slippage_cost"] == pytest.approx(0.0)  # 0 bps slippage

    def test_slippage_cost_nonzero_with_bps_slippage(self):
        from services.engines._runtime import run_strategy

        cfg = ExecutionConfig(
            commission=PercentageCommission(rate=0.0),
            slippage=FixedBpsSlippage(bps=10),
            fill=CurrentCloseDelayedFill(latency_bars=1),
        )
        code = """\
import pandas as pd
def run(ohlcv):
    entries = pd.Series(False, index=ohlcv.index)
    exits   = pd.Series(False, index=ohlcv.index)
    entries.iloc[0] = True
    exits.iloc[-2]  = True
    return {"entries": entries, "exits": exits}
"""
        rng = np.random.default_rng(8)
        n = 50
        close = 100.0 * np.cumprod(1 + rng.normal(0.001, 0.01, n))
        df = pd.DataFrame(
            {
                "open":   close,
                "high":   close * 1.005,
                "low":    close * 0.995,
                "close":  close,
                "volume": 1000.0,
            },
            index=pd.date_range("2023-01-01", periods=n, freq="D"),
        )
        _, trades, _ = run_strategy(code, df, execution_config=cfg)
        assert len(trades) == 1
        assert trades[0]["slippage_cost"] > 0
