"""
Execution model: commission, slippage, and fill protocols with concrete implementations.

Every backtest carries an ExecutionConfig; default_for_asset_class provides
realistic defaults per asset class.  Use ExecutionConfig(PercentageCommission(0),
FixedBpsSlippage(0), CurrentCloseDelayedFill()) to replicate the Phase 1
zero-friction baseline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import pandas as pd


# ── Commission models ─────────────────────────────────────────────────────────

@dataclass
class PercentageCommission:
    rate: float

    def fee(
        self, notional: float, shares: float, price: float, side: str = "buy"
    ) -> float:
        return notional * self.rate


@dataclass
class PerShareCommission:
    per_share: float
    min_per_order: float = 1.0

    def fee(
        self, notional: float, shares: float, price: float, side: str = "buy"
    ) -> float:
        return max(shares * self.per_share, self.min_per_order)


@dataclass
class TieredCommission:
    # Each tier: (lower_shares_inclusive, upper_shares_exclusive_or_None, rate)
    # Marginal tiering — each tier's rate applies only to shares in that bracket.
    tiers: List[Tuple[int, Optional[int], float]]

    def fee(
        self, notional: float, shares: float, price: float, side: str = "buy"
    ) -> float:
        total = 0.0
        remaining = shares
        for lower, upper, rate in self.tiers:
            if remaining <= 0:
                break
            bracket = (min(upper, shares) - lower) if upper is not None else remaining
            bracket = min(max(bracket, 0.0), remaining)
            total += bracket * price * rate
            remaining -= bracket
        return total


@dataclass
class AShareCommission:
    """A-share commission: base rate on all trades, stamp duty on sells only."""
    base_rate: float = 0.00025   # 0.025%
    stamp_rate: float = 0.001    # 0.1% stamp on sells

    def fee(
        self, notional: float, shares: float, price: float, side: str = "buy"
    ) -> float:
        stamp = self.stamp_rate if side == "sell" else 0.0
        return notional * (self.base_rate + stamp)


# ── Slippage models ───────────────────────────────────────────────────────────

@dataclass
class FixedBpsSlippage:
    bps: float

    def adjust(self, price: float, side: str, atr: float = 0.0) -> float:
        factor = self.bps / 1e4
        return price * (1 + factor) if side == "buy" else price * (1 - factor)


@dataclass
class SpreadSlippage:
    half_spread_bps: float

    def adjust(self, price: float, side: str, atr: float = 0.0) -> float:
        factor = self.half_spread_bps / 1e4
        return price * (1 + factor) if side == "buy" else price * (1 - factor)


@dataclass
class VolatilitySlippage:
    atr_multiplier: float

    def adjust(self, price: float, side: str, atr: float = 0.0) -> float:
        adj = atr * self.atr_multiplier
        return price + adj if side == "buy" else price - adj


# ── Fill models ───────────────────────────────────────────────────────────────

@dataclass
class NextBarOpenFill:
    latency_bars: int = 1

    def fill_price(self, df: pd.DataFrame, signal_bar: int, side: str) -> float:
        fill_bar = signal_bar + self.latency_bars
        if fill_bar >= len(df):
            return float(df["close"].iloc[-1])
        return float(df["open"].iloc[fill_bar])


@dataclass
class CurrentCloseDelayedFill:
    latency_bars: int = 1

    def fill_price(self, df: pd.DataFrame, signal_bar: int, side: str) -> float:
        fill_bar = signal_bar + self.latency_bars
        if fill_bar >= len(df):
            return float(df["close"].iloc[-1])
        return float(df["close"].iloc[fill_bar])


@dataclass
class VWAPSliceFill:
    """One-bar VWAP approximation: (open + high + low + close) / 4."""
    latency_bars: int = 1

    def fill_price(self, df: pd.DataFrame, signal_bar: int, side: str) -> float:
        fill_bar = signal_bar + self.latency_bars
        if fill_bar >= len(df):
            return float(df["close"].iloc[-1])
        row = df.iloc[fill_bar]
        return float((row["open"] + row["high"] + row["low"] + row["close"]) / 4)


# ── ExecutionConfig ───────────────────────────────────────────────────────────

@dataclass
class ExecutionConfig:
    commission: object  # CommissionModel
    slippage: object    # SlippageModel
    fill: object        # FillModel


# ── Asset-class defaults ──────────────────────────────────────────────────────

def default_for_asset_class(asset_class: str) -> ExecutionConfig:
    ac = asset_class.lower()
    if ac == "us_equity":
        return ExecutionConfig(
            commission=PercentageCommission(rate=0.0005),   # 0.05%
            slippage=FixedBpsSlippage(bps=1),
            fill=NextBarOpenFill(),
        )
    if ac == "a_share":
        return ExecutionConfig(
            commission=AShareCommission(base_rate=0.00025, stamp_rate=0.001),
            slippage=FixedBpsSlippage(bps=2),
            fill=NextBarOpenFill(),
        )
    if ac == "crypto":
        return ExecutionConfig(
            commission=PercentageCommission(rate=0.001),    # 0.1%
            slippage=FixedBpsSlippage(bps=2),
            fill=CurrentCloseDelayedFill(latency_bars=1),
        )
    if ac == "forex":
        return ExecutionConfig(
            commission=PercentageCommission(rate=0.0),
            slippage=FixedBpsSlippage(bps=5),               # ~0.5 pip on EUR/USD
            fill=NextBarOpenFill(),
        )
    # fallback
    return ExecutionConfig(
        commission=PercentageCommission(rate=0.001),
        slippage=FixedBpsSlippage(bps=2),
        fill=NextBarOpenFill(),
    )
