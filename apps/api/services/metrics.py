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
) -> Dict[str, Any]:
    if equity_curve.empty or len(equity_curve) < 2:
        return _null_metrics()

    returns = equity_curve.pct_change().dropna()
    if returns.empty:
        return _null_metrics()

    initial = float(equity_curve.iloc[0])
    final   = float(equity_curve.iloc[-1])
    ret_arr = returns.to_numpy(dtype=float)
    n_bars  = len(equity_curve)

    # ── Total return ──────────────────────────────────────────────────────────
    total_return = (final - initial) / initial if initial > 0 else None

    # ── CAGR ─────────────────────────────────────────────────────────────────
    n_years = n_bars / bars_per_year
    cagr = float((final / initial) ** (1.0 / n_years) - 1) if n_years > 0 and initial > 0 else None

    # ── Volatility (annualised, population std) ───────────────────────────────
    vol_std_pop = float(np.std(ret_arr, ddof=0))
    volatility = vol_std_pop * math.sqrt(bars_per_year) if len(ret_arr) > 1 else None

    # ── Downside volatility (sample std of negative returns) ─────────────────
    neg = ret_arr[ret_arr < 0]
    if len(neg) > 1:
        downside_volatility = float(np.std(neg, ddof=1) * math.sqrt(bars_per_year))
    else:
        downside_volatility = None

    # ── Sharpe (annualised, sample std) ───────────────────────────────────────
    sharpe_std = float(returns.std())  # pandas default: ddof=1
    sharpe = (
        float((returns.mean() / sharpe_std) * math.sqrt(bars_per_year))
        if sharpe_std > 1e-10 else None
    )

    # ── Sortino (annualised) ──────────────────────────────────────────────────
    down_std = float(np.std(neg, ddof=1)) if len(neg) > 1 else 0.0
    sortino  = (
        float((returns.mean() / down_std) * math.sqrt(bars_per_year))
        if down_std > 1e-10 else None
    )

    # ── VaR 95 ────────────────────────────────────────────────────────────────
    var_95 = float(-np.percentile(ret_arr, 5)) if len(ret_arr) > 0 else None

    # ── CVaR 95 ───────────────────────────────────────────────────────────────
    threshold = float(np.percentile(ret_arr, 5))
    tail = ret_arr[ret_arr <= threshold]
    cvar_95 = float(-tail.mean()) if len(tail) > 0 else None

    # ── Max drawdown ──────────────────────────────────────────────────────────
    rolling_max = equity_curve.expanding().max()
    dd_series   = (equity_curve - rolling_max) / rolling_max
    max_dd      = float(dd_series.min())

    # ── Max drawdown duration ─────────────────────────────────────────────────
    max_dd_duration = _max_drawdown_duration(equity_curve)

    # ── Calmar ratio ──────────────────────────────────────────────────────────
    if cagr is not None and max_dd < -1e-10:
        calmar_ratio = float(cagr / abs(max_dd))
    else:
        calmar_ratio = None

    # ── Omega ratio ───────────────────────────────────────────────────────────
    pos_sum = float(ret_arr[ret_arr > 0].sum())
    neg_sum = float(abs(ret_arr[ret_arr < 0].sum()))
    omega_ratio = float(pos_sum / neg_sum) if neg_sum > 1e-10 else None

    # ── Tail ratio ────────────────────────────────────────────────────────────
    p95 = float(np.percentile(ret_arr, 95))
    p05 = float(np.percentile(ret_arr, 5))
    if abs(p05) > 1e-10:
        tail_ratio = float(abs(p95) / abs(p05))
    else:
        tail_ratio = None

    # ── Trade statistics ──────────────────────────────────────────────────────
    total_trades = len(trades)
    win_rate = None
    profit_factor = None
    avg_win = None
    avg_loss = None
    largest_win = None
    largest_loss = None
    avg_trade_duration_bars = None
    exposure_pct = None
    turnover = None

    if total_trades > 0:
        winners = [t for t in trades if t.get("pnl", 0) > 0]
        losers  = [t for t in trades if t.get("pnl", 0) < 0]

        win_rate = float(len(winners) / total_trades)

        gross_profit = sum(t["pnl"] for t in winners) if winners else 0.0
        gross_loss   = abs(sum(t["pnl"] for t in losers)) if losers else 0.0
        profit_factor = float(gross_profit / gross_loss) if gross_loss > 1e-10 else None

        avg_win  = float(sum(t["pnl"] for t in winners) / len(winners)) if winners else None
        avg_loss = float(sum(abs(t["pnl"]) for t in losers) / len(losers)) if losers else None

        largest_win  = float(max(t["pnl"] for t in trades)) if any(t["pnl"] > 0 for t in trades) else None
        largest_loss = float(min(t["pnl"] for t in trades)) if any(t["pnl"] < 0 for t in trades) else None

        bars_held_list = [t["bars_held"] for t in trades if "bars_held" in t]
        if bars_held_list:
            avg_trade_duration_bars = float(sum(bars_held_list) / len(bars_held_list))

        total_bars_held = sum(t.get("bars_held", 0) for t in trades)
        exposure_pct = float(total_bars_held / n_bars) if n_bars > 0 else None
        turnover     = float(2 * total_trades / n_bars) if n_bars > 0 else None
    else:
        exposure_pct = 0.0
        turnover     = 0.0

    return {
        # core
        "schema_version":            2,
        "final_value":               final,
        "total_return":              total_return,
        "cagr":                      cagr,
        # risk
        "volatility":                volatility,
        "downside_volatility":       downside_volatility,
        "sharpe_ratio":              sharpe,
        "sortino_ratio":             sortino,
        "var_95":                    var_95,
        "cvar_95":                   cvar_95,
        "max_drawdown":              max_dd,
        "max_drawdown_duration_days": max_dd_duration,
        "calmar_ratio":              calmar_ratio,
        # distribution
        "omega_ratio":               omega_ratio,
        "tail_ratio":                tail_ratio,
        # trade quality
        "win_rate":                  win_rate,
        "total_trades":              total_trades if total_trades > 0 else None,
        "profit_factor":             profit_factor,
        "avg_win":                   avg_win,
        "avg_loss":                  avg_loss,
        "largest_win":               largest_win,
        "largest_loss":              largest_loss,
        "avg_trade_duration_bars":   avg_trade_duration_bars,
        # exposure
        "exposure_pct":              exposure_pct,
        "turnover":                  turnover,
    }


def _max_drawdown_duration(equity: pd.Series) -> int:
    peak = equity.iloc[0]
    current_duration = 0
    max_duration = 0
    for val in equity:
        if val >= peak:
            peak = val
            current_duration = 0
        else:
            current_duration += 1
            if current_duration > max_duration:
                max_duration = current_duration
    return max_duration


def _null_metrics() -> Dict[str, Any]:
    return {k: None for k in [
        "schema_version", "final_value", "total_return", "cagr",
        "volatility", "downside_volatility", "sharpe_ratio", "sortino_ratio",
        "var_95", "cvar_95", "max_drawdown", "max_drawdown_duration_days",
        "calmar_ratio", "omega_ratio", "tail_ratio",
        "win_rate", "total_trades", "profit_factor",
        "avg_win", "avg_loss", "largest_win", "largest_loss",
        "avg_trade_duration_bars", "exposure_pct", "turnover",
    ]}
