"""
Computes standard backtest performance metrics from an equity curve and
a list of closed trades.

All inputs are plain Python/numpy — no VectorBT or Backtrader dependency.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


def compute_metrics(
    equity_curve: pd.Series,
    trades: List[Dict[str, Any]],
    bars_per_year: int = 252,
) -> Dict[str, Optional[float]]:
    """
    Args:
        equity_curve: portfolio value indexed by bar (pd.Series).
        trades: list of dicts with keys: entry_price, exit_price, side, pnl.
        bars_per_year: 252 for daily, 365 for crypto daily, 52 for weekly.

    Returns dict matching BacktestMetrics schema.
    """
    if equity_curve.empty or len(equity_curve) < 2:
        return _null_metrics()

    returns = equity_curve.pct_change().dropna()
    if returns.empty:
        return _null_metrics()

    # ── Sharpe ratio (annualised) ──────────────────────────────────────────
    std = returns.std()
    sharpe = float((returns.mean() / std) * math.sqrt(bars_per_year)) if std > 1e-10 else None

    # ── Sortino ratio (annualised, downside std only) ─────────────────────
    downside = returns[returns < 0]
    down_std = downside.std()
    sortino = (
        float((returns.mean() / down_std) * math.sqrt(bars_per_year))
        if len(downside) > 1 and down_std > 1e-10
        else None
    )

    # ── CAGR ──────────────────────────────────────────────────────────────
    n_years = len(equity_curve) / bars_per_year
    initial = float(equity_curve.iloc[0])
    final = float(equity_curve.iloc[-1])
    cagr = float((final / initial) ** (1.0 / n_years) - 1) if n_years > 0 and initial > 0 else None

    # ── Max drawdown ──────────────────────────────────────────────────────
    rolling_max = equity_curve.expanding().max()
    dd_series = (equity_curve - rolling_max) / rolling_max
    max_dd = float(dd_series.min())

    # ── Trade statistics ──────────────────────────────────────────────────
    total_trades = len(trades)
    if total_trades > 0:
        winners = [t for t in trades if t.get("pnl", 0) > 0]
        losers  = [t for t in trades if t.get("pnl", 0) < 0]
        win_rate = float(len(winners) / total_trades)

        gross_profit = sum(t["pnl"] for t in winners) if winners else 0.0
        gross_loss   = abs(sum(t["pnl"] for t in losers)) if losers else 0.0
        profit_factor = float(gross_profit / gross_loss) if gross_loss > 1e-10 else None
    else:
        win_rate = None
        profit_factor = None

    return {
        "sharpe_ratio":   sharpe,
        "sortino_ratio":  sortino,
        "cagr":           cagr,
        "max_drawdown":   max_dd,
        "win_rate":       win_rate,
        "total_trades":   total_trades if total_trades > 0 else None,
        "profit_factor":  profit_factor,
        "final_value":    final,
    }


def _null_metrics() -> Dict[str, Optional[float]]:
    return {
        "sharpe_ratio": None, "sortino_ratio": None, "cagr": None,
        "max_drawdown": None, "win_rate": None, "total_trades": None,
        "profit_factor": None, "final_value": None,
    }
