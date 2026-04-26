"""
Engine runtime — the single in-process execution path for SimpleEngine.

sandbox=True  → subprocess sandbox (default, Phase 2 Task 0.C).
sandbox=False → direct exec with _SAFE_BUILTINS (only for internal benchmarks
                and the golden-test arbiter, never the API path).

Until Task 0.C lands, sandbox is always effectively False (subprocess not yet built).
The API response will carry sandbox="in_process" until then.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from schemas.data import OHLCVBar
from services.engines.exceptions import EngineError
from services.engines.execution_model import (
    CurrentCloseDelayedFill,
    ExecutionConfig,
    FixedBpsSlippage,
    PercentageCommission,
)
from services.engines.strategy_contract import validate_result
from services.metrics import compute_metrics
from services.python_validator import _ALLOWED_IMPORTS, validate

import builtins as _builtins_module
_REAL_IMPORT = _builtins_module.__import__


def _safe_import(name: str, *args: Any, **kwargs: Any) -> Any:
    root = name.split(".")[0]
    if root not in _ALLOWED_IMPORTS:
        raise ImportError(f"import '{name}' is not allowed in strategy code")
    return _REAL_IMPORT(name, *args, **kwargs)


_SAFE_BUILTINS: Dict[str, Any] = {
    "__import__": _safe_import,
    "len": len, "range": range, "enumerate": enumerate,
    "zip": zip, "map": map, "filter": filter, "sorted": sorted,
    "list": list, "dict": dict, "set": set, "tuple": tuple,
    "int": int, "float": float, "str": str, "bool": bool,
    "max": max, "min": min, "sum": sum, "abs": abs, "round": round,
    "any": any, "all": all, "isinstance": isinstance,
    "print": lambda *a, **kw: None,
    "None": None, "True": True, "False": False,
    "NotImplementedError": NotImplementedError,
    "ValueError": ValueError,
}


def _default_execution_config() -> ExecutionConfig:
    # Reproduces Phase 1 behaviour: fill at next-bar close, 0.1% commission, 0 slippage.
    return ExecutionConfig(
        commission=PercentageCommission(rate=0.001),
        slippage=FixedBpsSlippage(bps=0),
        fill=CurrentCloseDelayedFill(latency_bars=1),
    )


def run_strategy(
    code: str,
    ohlcv_df: pd.DataFrame,
    initial_capital: float = 100_000.0,
    *,
    execution_config: Optional[ExecutionConfig] = None,
    sandbox: bool = False,
) -> Tuple[Dict[str, Optional[float]], List[Dict[str, Any]], pd.Series]:
    """
    Execute strategy code and simulate trades.

    Returns (metrics_dict, trades_list, equity_series).
    Raises EngineError on execution or logic failure.
    """
    if sandbox:
        raise NotImplementedError(
            "Subprocess sandbox requires calling run_in_sandbox() directly "
            "(it is async; run_strategy is sync). Use services.engines.sandbox.run_in_sandbox."
        )

    valid, errors = validate(code)
    if not valid:
        raise EngineError("Validation failed: " + "; ".join(errors))

    exec_globals: Dict[str, Any] = {
        "__builtins__": _SAFE_BUILTINS,
        "np": np, "numpy": np,
        "pd": pd, "pandas": pd,
        "math": math,
    }
    try:
        exec(compile(code, "<strategy>", "exec"), exec_globals)  # noqa: S102
    except Exception as exc:
        raise EngineError(f"Execution error: {exc}") from exc

    run_fn = exec_globals.get("run")
    if not callable(run_fn):
        raise EngineError("run() function not found after execution")

    try:
        raw = run_fn(ohlcv_df.copy())
    except Exception as exc:
        raise EngineError(f"Strategy runtime error: {exc}") from exc

    result  = validate_result(raw)
    entries = result["entries"].reindex(ohlcv_df.index, fill_value=False).astype(bool)
    exits   = result["exits"].reindex(ohlcv_df.index, fill_value=False).astype(bool)
    cfg     = execution_config or _default_execution_config()

    equity, trades = _simulate(ohlcv_df, entries, exits, initial_capital, cfg)
    bars_per_year  = _infer_bars_per_year(ohlcv_df)
    metrics        = compute_metrics(equity, trades, bars_per_year=bars_per_year)

    return metrics, trades, equity


def _simulate(
    df: pd.DataFrame,
    entries: pd.Series,
    exits: pd.Series,
    initial_capital: float,
    cfg: ExecutionConfig,
) -> Tuple[pd.Series, List[Dict[str, Any]]]:
    close = df["close"].values
    n     = len(close)
    atr   = _compute_atr(df)
    lat   = cfg.fill.latency_bars

    cash      = initial_capital
    position  = 0.0
    entry_px  = 0.0
    entry_fee = 0.0
    entry_bar = -1
    min_close = 0.0
    max_close = 0.0
    equity    = np.empty(n, dtype=float)
    trades: List[Dict[str, Any]] = []

    for i in range(n):
        signal_bar = i - lat

        # update MAE/MFE trackers while in position
        if position > 0.0:
            c = close[i]
            if c < min_close:
                min_close = c
            if c > max_close:
                max_close = c

        if signal_bar >= 0 and entries.iloc[signal_bar] and position == 0.0:
            raw_px    = cfg.fill.fill_price(df, signal_bar, "buy")
            fill_px   = cfg.slippage.adjust(raw_px, "buy", atr=float(atr[i]))
            shares    = cash / fill_px
            fee       = cfg.commission.fee(cash, shares, fill_px, "buy")
            position  = (cash - fee) / fill_px
            entry_px  = fill_px
            entry_fee = fee
            entry_bar = i
            min_close = close[i]
            max_close = close[i]
            cash      = 0.0

        if signal_bar >= 0 and exits.iloc[signal_bar] and position > 0.0:
            raw_px        = cfg.fill.fill_price(df, signal_bar, "sell")
            fill_px       = cfg.slippage.adjust(raw_px, "sell", atr=float(atr[i]))
            proceeds      = position * fill_px
            fee           = cfg.commission.fee(proceeds, position, fill_px, "sell")
            slippage_cost = abs(raw_px - fill_px) * position
            net_proceeds  = proceeds - fee
            pnl           = net_proceeds - (position * entry_px + entry_fee)
            trades.append({
                "entry_price":   entry_px,
                "exit_price":    fill_px,
                "pnl":           pnl,
                "side":          "long",
                "fees":          entry_fee + fee,
                "slippage_cost": slippage_cost,
                "entry_time":    str(df.index[entry_bar]),
                "exit_time":     str(df.index[i]),
                "quantity":      position,
                "pnl_pct":       (fill_px - entry_px) / entry_px,
                "bars_held":     i - entry_bar,
                "mae":           (min_close - entry_px) / entry_px,
                "mfe":           (max_close - entry_px) / entry_px,
            })
            cash      = net_proceeds
            position  = 0.0
            entry_px  = 0.0
            entry_fee = 0.0
            entry_bar = -1

        equity[i] = cash + position * close[i]

    if position > 0.0:
        raw_px        = close[-1]
        fill_px       = cfg.slippage.adjust(raw_px, "sell", atr=float(atr[-1]))
        proceeds      = position * fill_px
        fee           = cfg.commission.fee(proceeds, position, fill_px, "sell")
        slippage_cost = abs(raw_px - fill_px) * position
        net_proceeds  = proceeds - fee
        pnl           = net_proceeds - (position * entry_px + entry_fee)
        trades.append({
            "entry_price":   entry_px,
            "exit_price":    fill_px,
            "pnl":           pnl,
            "side":          "long",
            "fees":          entry_fee + fee,
            "slippage_cost": slippage_cost,
            "entry_time":    str(df.index[entry_bar]),
            "exit_time":     str(df.index[-1]),
            "quantity":      position,
            "pnl_pct":       (fill_px - entry_px) / entry_px,
            "bars_held":     (n - 1) - entry_bar,
            "mae":           (min_close - entry_px) / entry_px,
            "mfe":           (max_close - entry_px) / entry_px,
        })
        equity[-1] = cash + net_proceeds

    return pd.Series(equity, index=df.index), trades


def _compute_atr(df: pd.DataFrame, period: int = 14) -> np.ndarray:
    high  = df["high"].values
    low   = df["low"].values
    close = df["close"].values
    n     = len(close)
    tr    = np.empty(n)
    tr[0] = high[0] - low[0]
    for i in range(1, n):
        tr[i] = max(high[i] - low[i], abs(high[i] - close[i-1]), abs(low[i] - close[i-1]))
    atr = np.empty(n)
    atr[0] = tr[0]
    k = 1.0 / period
    for i in range(1, n):
        atr[i] = atr[i-1] * (1 - k) + tr[i] * k
    return atr


def _infer_bars_per_year(df: pd.DataFrame) -> int:
    if len(df) < 2:
        return 252
    try:
        idx   = pd.to_datetime(df.index)
        delta = (idx[-1] - idx[0]).days
        if delta <= 0:
            return 252
        bpy = len(df) / delta * 365
        if bpy < 20:  return 12
        if bpy < 80:  return 52
        if bpy < 200: return 126
        if bpy < 300: return 252
        if bpy < 500: return 365
        return int(bpy)
    except Exception:
        return 252


def bars_to_df(bars: list[OHLCVBar]) -> pd.DataFrame:
    rows = [
        {"timestamp": b.timestamp, "open": b.open, "high": b.high,
         "low": b.low, "close": b.close, "volume": b.volume}
        for b in bars
    ]
    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df.set_index("timestamp")


def sample_equity(equity: pd.Series, max_points: int = 300) -> list[list]:
    n = len(equity)
    if n == 0:
        return []
    step = max(1, n // max_points)
    sampled = equity.iloc[::step]
    return [[str(idx), float(val)] for idx, val in sampled.items()]
