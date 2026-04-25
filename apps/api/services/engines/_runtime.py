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


def run_strategy(
    code: str,
    ohlcv_df: pd.DataFrame,
    initial_capital: float = 100_000.0,
    commission: float = 0.001,
    *,
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

    result = validate_result(raw)
    entries = result["entries"].reindex(ohlcv_df.index, fill_value=False).astype(bool)
    exits   = result["exits"].reindex(ohlcv_df.index, fill_value=False).astype(bool)

    equity, trades = _simulate(ohlcv_df, entries, exits, initial_capital, commission)
    bars_per_year  = _infer_bars_per_year(ohlcv_df)
    metrics        = compute_metrics(equity, trades, bars_per_year=bars_per_year)

    return metrics, trades, equity


def _simulate(
    df: pd.DataFrame,
    entries: pd.Series,
    exits: pd.Series,
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

        if i > 0 and entries.iloc[i - 1] and position == 0.0:
            size     = cash / (price * (1 + commission))
            cost     = size * price * (1 + commission)
            cash    -= cost
            position = size
            entry_px = price

        if i > 0 and exits.iloc[i - 1] and position > 0.0:
            proceeds   = position * price * (1 - commission)
            cost_basis = position * entry_px * (1 + commission)
            pnl        = proceeds - cost_basis
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

    if position > 0.0:
        price      = close[-1]
        proceeds   = position * price * (1 - commission)
        cost_basis = position * entry_px * (1 + commission)
        pnl        = proceeds - cost_basis
        trades.append({
            "entry_price": entry_px,
            "exit_price":  price,
            "pnl":         pnl,
            "side":        "long",
        })
        equity[-1] = cash + proceeds

    return pd.Series(equity, index=df.index), trades


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
