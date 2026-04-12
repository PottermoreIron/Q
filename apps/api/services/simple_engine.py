"""
Simple backtesting engine.

Executes the user's run(ohlcv) function in a restricted Python environment,
simulates trades from the entry/exit signals, and returns an equity curve
and trade list for metrics computation.

This engine handles all asset classes. VectorBT / Backtrader integration
(Phase 4+) will replace this for production-scale runs while keeping this
as the fast dev/preview engine.

Security model:
  - The code is validated by python_validator.py before reaching here.
  - Execution uses a restricted __builtins__ dict (no file/network/exec).
  - Compute timeout is enforced by the Celery worker (not here).
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from services.metrics import compute_metrics
from services.python_validator import _ALLOWED_IMPORTS, validate

import builtins as _builtins_module
_REAL_IMPORT = _builtins_module.__import__


def _safe_import(name: str, *args: Any, **kwargs: Any) -> Any:
    root = name.split(".")[0]
    if root not in _ALLOWED_IMPORTS:
        raise ImportError(f"import '{name}' is not allowed in strategy code")
    return _REAL_IMPORT(name, *args, **kwargs)


# Only safe builtins allowed inside strategy code
_SAFE_BUILTINS: Dict[str, Any] = {
    "__import__": _safe_import,
    "len": len, "range": range, "enumerate": enumerate,
    "zip": zip, "map": map, "filter": filter, "sorted": sorted,
    "list": list, "dict": dict, "set": set, "tuple": tuple,
    "int": int, "float": float, "str": str, "bool": bool,
    "max": max, "min": min, "sum": sum, "abs": abs, "round": round,
    "any": any, "all": all, "isinstance": isinstance,
    "print": lambda *a, **kw: None,   # silenced
    "None": None, "True": True, "False": False,
    "NotImplementedError": NotImplementedError,
    "ValueError": ValueError,
}


class EngineError(Exception):
    pass


def run_strategy(
    code: str,
    ohlcv_df: pd.DataFrame,
    initial_capital: float = 100_000.0,
    commission: float = 0.001,       # 0.1% per trade
) -> Tuple[Dict[str, Optional[float]], List[Dict[str, Any]], pd.Series]:
    """
    Execute strategy code and simulate trades.

    Returns:
        (metrics_dict, trades_list, equity_curve)

    Raises EngineError on execution or logic failure.
    """
    # 1. Validate before exec
    valid, errors = validate(code)
    if not valid:
        raise EngineError("Validation failed: " + "; ".join(errors))

    # 2. Execute in restricted environment
    exec_globals: Dict[str, Any] = {
        "__builtins__": _SAFE_BUILTINS,
        "np": np,
        "numpy": np,
        "pd": pd,
        "pandas": pd,
        "math": math,
    }
    try:
        exec(compile(code, "<strategy>", "exec"), exec_globals)  # noqa: S102
    except Exception as exc:
        raise EngineError(f"Execution error: {exc}") from exc

    run_fn = exec_globals.get("run")
    if not callable(run_fn):
        raise EngineError("run() function not found after execution")

    # 3. Call run(ohlcv)
    try:
        result = run_fn(ohlcv_df.copy())
    except Exception as exc:
        raise EngineError(f"Strategy runtime error: {exc}") from exc

    if not isinstance(result, dict):
        raise EngineError("run() must return a dict with 'entries' and 'exits' keys")

    entries: pd.Series = result.get("entries", pd.Series(dtype=bool))
    exits:   pd.Series = result.get("exits",   pd.Series(dtype=bool))

    if not isinstance(entries, pd.Series) or not isinstance(exits, pd.Series):
        raise EngineError("'entries' and 'exits' must be pandas Series of booleans")

    # Align to ohlcv index
    entries = entries.reindex(ohlcv_df.index, fill_value=False).astype(bool)
    exits   = exits.reindex(ohlcv_df.index, fill_value=False).astype(bool)

    # 4. Simulate trades (vectorised, long-only for now)
    equity, trades = _simulate(ohlcv_df, entries, exits, initial_capital, commission)

    # 5. Compute metrics
    asset_class = "stock"  # default bars_per_year
    bars_per_year = _infer_bars_per_year(ohlcv_df)
    metrics = compute_metrics(equity, trades, bars_per_year=bars_per_year)

    return metrics, trades, equity


def _simulate(
    df: pd.DataFrame,
    entries: pd.Series,
    exits:   pd.Series,
    initial_capital: float,
    commission: float,
) -> Tuple[pd.Series, List[Dict[str, Any]]]:
    close = df["close"].values
    n     = len(close)

    cash     = initial_capital
    position = 0.0
    entry_px = 0.0
    equity   = np.empty(n, dtype=float)
    trades: List[Dict[str, Any]] = []

    for i in range(n):
        price = close[i]

        # Enter: next bar after signal (i-1 fires, i executes)
        if i > 0 and entries.iloc[i - 1] and position == 0.0:
            size      = cash / price
            cost      = size * price * (1 + commission)
            if cost <= cash:
                cash     -= cost
                position  = size
                entry_px  = price

        # Exit: next bar after signal
        if i > 0 and exits.iloc[i - 1] and position > 0.0:
            proceeds = position * price * (1 - commission)
            pnl      = proceeds - (position * entry_px)
            trades.append({
                "entry_price": entry_px,
                "exit_price":  price,
                "pnl":         pnl,
                "side":        "long",
            })
            cash     += proceeds
            position  = 0.0
            entry_px  = 0.0

        equity[i] = cash + position * price

    # Close open position at last bar
    if position > 0.0:
        price    = close[-1]
        proceeds = position * price * (1 - commission)
        pnl      = proceeds - (position * entry_px)
        trades.append({
            "entry_price": entry_px,
            "exit_price":  price,
            "pnl":         pnl,
            "side":        "long",
        })
        equity[-1] = cash + proceeds

    return pd.Series(equity, index=df.index), trades


def _infer_bars_per_year(df: pd.DataFrame) -> int:
    """Heuristically infer trading bars per year from the DataFrame index."""
    if len(df) < 2:
        return 252
    try:
        idx = pd.to_datetime(df.index)
        delta = (idx[-1] - idx[0]).days
        if delta <= 0:
            return 252
        bpy = len(df) / delta * 365
        # Snap to known values
        if bpy < 20:    return 12    # monthly
        if bpy < 80:    return 52    # weekly
        if bpy < 200:   return 126   # bi-daily
        if bpy < 300:   return 252   # daily stocks
        if bpy < 500:   return 365   # daily crypto
        return int(bpy)
    except Exception:
        return 252
