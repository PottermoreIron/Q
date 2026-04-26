"""
VectorBT engine — vectorised backtesting for crypto and multi-asset quant.

Requires: vectorbt==0.26.2, numba>=0.53.1,<0.57.0, plotly>=5.0,<6.0
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from schemas.data import OHLCVBar
from services.engines._runtime import (
    _SAFE_BUILTINS,
    _infer_bars_per_year,
    sample_equity,
)
from services.engines.exceptions import EngineError
from services.engines.execution_model import ExecutionConfig, FixedBpsSlippage, PercentageCommission
from services.engines.protocol import BacktestResult
from services.engines.strategy_contract import validate_result
from services.metrics import compute_metrics
from services.python_validator import validate


_DEFAULT_CFG = ExecutionConfig(
    commission=PercentageCommission(rate=0.001),
    slippage=FixedBpsSlippage(bps=0),
    fill=None,
)


class VectorBTEngine:
    def __init__(self, execution_config: Optional[ExecutionConfig] = None) -> None:
        self._cfg = execution_config or _DEFAULT_CFG

    async def run(
        self,
        strategy_code: str,
        bars: list[OHLCVBar],
    ) -> BacktestResult:
        if not isinstance(self._cfg.commission, PercentageCommission):
            raise EngineError(
                f"VectorBTEngine only supports PercentageCommission; "
                f"got {type(self._cfg.commission).__name__}. "
                f"Switch to PercentageCommission or use SimpleEngine."
            )

        import vectorbt as vbt  # deferred — optional dependency

        valid, errors = validate(strategy_code)
        if not valid:
            raise EngineError("Validation failed: " + "; ".join(errors))

        df    = _bars_to_df(bars)
        close = df["close"]

        exec_globals: Dict[str, Any] = {
            "__builtins__": _SAFE_BUILTINS,
            "np": np, "numpy": np,
            "pd": pd, "pandas": pd,
            "math": math,
        }
        try:
            exec(compile(strategy_code, "<strategy>", "exec"), exec_globals)  # noqa: S102
        except Exception as exc:
            raise EngineError(f"Execution error: {exc}") from exc

        run_fn = exec_globals.get("run")
        if not callable(run_fn):
            raise EngineError("run() function not found after execution")

        try:
            raw = run_fn(df.copy())
        except Exception as exc:
            raise EngineError(f"Strategy runtime error: {exc}") from exc

        result  = validate_result(raw)
        entries = result["entries"].reindex(df.index, fill_value=False).astype(bool)
        exits   = result["exits"].reindex(df.index, fill_value=False).astype(bool)
        sl_stop = result.get("stop_loss_pct")
        tp_stop = result.get("take_profit_pct")

        pf_kwargs: Dict[str, Any] = dict(
            close=close,
            entries=entries,
            exits=exits,
            fees=self._cfg.commission.rate,
            slippage=self._cfg.slippage.bps / 1e4,
            init_cash=100_000.0,
            freq="D",
        )
        if sl_stop is not None:
            pf_kwargs["sl_stop"] = sl_stop
        if tp_stop is not None:
            pf_kwargs["tp_stop"] = tp_stop

        try:
            pf = vbt.Portfolio.from_signals(**pf_kwargs)
        except Exception as exc:
            raise EngineError(f"VectorBT simulation error: {exc}") from exc

        equity = pf.value()
        trades = _extract_trades(pf, close.values, close.index)
        metrics = compute_metrics(equity, trades, bars_per_year=_infer_bars_per_year(df))

        return BacktestResult(
            engine="vectorbt",
            metrics=metrics,
            trades=list(trades[:500]),
            equity_curve=sample_equity(equity),
        )


def _bars_to_df(bars: list[OHLCVBar]) -> pd.DataFrame:
    """Faster alternative to _runtime.bars_to_df using fromiter + direct DatetimeIndex."""
    n = len(bars)
    ts    = np.fromiter((b.timestamp for b in bars), dtype="int64",   count=n)
    opens = np.fromiter((b.open      for b in bars), dtype="float64", count=n)
    highs = np.fromiter((b.high      for b in bars), dtype="float64", count=n)
    lows  = np.fromiter((b.low       for b in bars), dtype="float64", count=n)
    closes= np.fromiter((b.close     for b in bars), dtype="float64", count=n)
    vols  = np.fromiter((b.volume    for b in bars), dtype="float64", count=n)
    # Avoid pd.to_datetime(unit='ms') overhead: multiply ms→ns and construct directly.
    idx = pd.DatetimeIndex(ts * 1_000_000, dtype="datetime64[ns]")
    return pd.DataFrame(
        {"open": opens, "high": highs, "low": lows, "close": closes, "volume": vols},
        index=idx,
    )


def _extract_trades(
    pf: Any,
    close_arr: np.ndarray,
    close_idx: pd.Index,
) -> List[Dict[str, Any]]:
    records = pf.trades.records_arr
    if len(records) == 0:
        return []

    trades: List[Dict[str, Any]] = []
    for rec in records:
        entry_idx = int(rec["entry_idx"])
        exit_idx  = int(rec["exit_idx"])
        entry_px  = float(rec["entry_price"])
        exit_px   = float(rec["exit_price"])

        window = close_arr[entry_idx : exit_idx + 1]
        if len(window) > 0:
            mae = float((window.min() - entry_px) / entry_px)
            mfe = float((window.max() - entry_px) / entry_px)
        else:
            mae = 0.0
            mfe = 0.0

        trades.append({
            "entry_price":   entry_px,
            "exit_price":    exit_px,
            "pnl":           float(rec["pnl"]),
            "side":          "long",
            "fees":          float(rec["entry_fees"] + rec["exit_fees"]),
            "slippage_cost": 0.0,
            "entry_time":    str(close_idx[entry_idx]),
            "exit_time":     str(close_idx[exit_idx]),
            "quantity":      float(rec["size"]),
            "pnl_pct":       (exit_px - entry_px) / entry_px,
            "bars_held":     exit_idx - entry_idx,
            "mae":           mae,
            "mfe":           mfe,
        })

    return trades
