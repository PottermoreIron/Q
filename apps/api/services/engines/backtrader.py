"""
Backtrader engine — event-driven backtesting for stocks, forex, futures.
"""
from __future__ import annotations

import asyncio
import math
from typing import Any, Dict, List, Optional, Type

import numpy as np
import pandas as pd

from schemas.data import OHLCVBar
from services.engines._runtime import (
    _SAFE_BUILTINS,
    _infer_bars_per_year,
    sample_equity,
)
from services.engines.exceptions import EngineError
from services.engines.execution_model import (
    AShareCommission as AShareComm,
    ExecutionConfig,
    FixedBpsSlippage,
    NextBarOpenFill,
    PercentageCommission as PctComm,
    PerShareCommission as PerShareComm,
    TieredCommission as TieredComm,
)
from services.engines.protocol import BacktestResult
from services.engines.strategy_contract import validate_result
from services.metrics import compute_metrics
from services.python_validator import validate


_DEFAULT_CFG = ExecutionConfig(
    commission=PctComm(rate=0.001),
    slippage=FixedBpsSlippage(bps=0),
    fill=NextBarOpenFill(),
)


# ── Custom commission info subclasses ─────────────────────────────────────────

def _make_per_share_comminfo(per_share: float, min_per_order: float):
    import backtrader as bt

    class _C(bt.CommInfoBase):
        def _getcommission(self, size, price, pseudoexec):
            return max(abs(size) * per_share, min_per_order)

    return _C()


def _make_tiered_comminfo(tiers):
    import backtrader as bt

    class _C(bt.CommInfoBase):
        def _getcommission(self, size, price, pseudoexec):
            shares = abs(size)
            total = 0.0
            remaining = shares
            for lower, upper, rate in tiers:
                if remaining <= 0:
                    break
                bracket = (min(upper, shares) - lower) if upper is not None else remaining
                bracket = min(max(bracket, 0.0), remaining)
                total += bracket * price * rate
                remaining -= bracket
            return total

    return _C()


def _make_ashare_comminfo(base_rate: float, stamp_rate: float):
    import backtrader as bt

    class _C(bt.CommInfoBase):
        def _getcommission(self, size, price, pseudoexec):
            notional = abs(size) * price
            stamp = stamp_rate if size < 0 else 0.0
            return notional * (base_rate + stamp)

    return _C()


# ── Strategy factory ──────────────────────────────────────────────────────────

def _make_signal_strategy(
    entries: np.ndarray,
    exits: np.ndarray,
    sl_pct: Optional[float],
    tp_pct: Optional[float],
    datetime_idx: pd.DatetimeIndex,
) -> type:
    """Returns a bt.Strategy subclass with signals and datetime index baked in via closure."""

    class SignalStrategy:  # populated below to avoid bt.Strategy metaclass at import time
        pass

    import backtrader as bt

    class SignalStrategy(bt.Strategy):  # type: ignore[no-redef]
        def __init__(self_):
            self_._equity: List[float] = []
            self_._trades_out: List[Dict[str, Any]] = []
            # Per-trade state (one position at a time)
            self_._entry_price: float = 0.0
            self_._entry_bar: int = 0
            self_._entry_size: float = 0.0
            self_._entry_commission: float = 0.0
            self_._pending_exit_price: Optional[float] = None
            self_._pending_exit_commission: float = 0.0
            # MAE/MFE tracking
            self_._min_close: float = float("inf")
            self_._max_close: float = float("-inf")

        def notify_order(self_, order) -> None:
            if order.status != order.Completed:
                return
            if order.isbuy():
                self_._entry_size = float(abs(order.executed.size))
                self_._entry_price = float(order.executed.price)
                self_._entry_commission = float(order.executed.comm)
                # 0-indexed bar number = bars collected so far (next() hasn't run yet)
                self_._entry_bar = len(self_._equity)
                self_._min_close = float(self_.data.close[0])
                self_._max_close = float(self_.data.close[0])
            elif order.issell():
                self_._pending_exit_price = float(order.executed.price)
                self_._pending_exit_commission = float(order.executed.comm)

        def notify_trade(self_, trade) -> None:
            if not trade.isclosed:
                return
            self_._record_trade(trade.baropen - 1, trade.barclose - 1, float(trade.pnlcomm))

        def next(self_) -> None:
            bar = len(self_._equity)
            self_._equity.append(float(self_.broker.getvalue()))

            if self_.position:
                c = float(self_.data.close[0])
                if c < self_._min_close:
                    self_._min_close = c
                if c > self_._max_close:
                    self_._max_close = c

            # SL/TP before signal exits
            if self_.position and sl_pct is not None and self_._entry_price > 0:
                pct = (float(self_.data.close[0]) - self_._entry_price) / self_._entry_price
                if pct <= -sl_pct:
                    self_.close()
                    return

            if self_.position and tp_pct is not None and self_._entry_price > 0:
                pct = (float(self_.data.close[0]) - self_._entry_price) / self_._entry_price
                if pct >= tp_pct:
                    self_.close()
                    return

            if bar >= len(entries):
                return

            if not self_.position and entries[bar]:
                cash = float(self_.broker.getcash())
                price = float(self_.data.close[0])
                if price > 0:
                    size = int(cash * 0.99 / price)
                    if size > 0:
                        self_.buy(size=size)
            elif self_.position and exits[bar]:
                self_.close()

        def stop(self_) -> None:
            """Force-record any position still open at end of data."""
            if not self_.position or self_._entry_price <= 0:
                return
            exit_bar_0 = max(len(self_._equity) - 1, self_._entry_bar)
            exit_px = float(self_.data.close[0])

            # Update MAE/MFE for the final bar
            self_._min_close = min(self_._min_close, exit_px)
            self_._max_close = max(self_._max_close, exit_px)

            try:
                ci = self_.broker.getcommissioninfo(self_.data)
                exit_comm = float(ci.getcommission(-self_._entry_size, exit_px))
            except Exception:
                exit_comm = 0.0

            net_pnl = (
                self_._entry_size * (exit_px - self_._entry_price)
                - self_._entry_commission
                - exit_comm
            )
            total_fees = self_._entry_commission + exit_comm
            entry_bar_0 = self_._entry_bar

            raw_mae = (self_._min_close - self_._entry_price) / self_._entry_price
            raw_mfe = (self_._max_close - self_._entry_price) / self_._entry_price

            n = len(datetime_idx)
            entry_ts = str(datetime_idx[entry_bar_0]) if 0 <= entry_bar_0 < n else ""
            exit_ts  = str(datetime_idx[exit_bar_0])  if 0 <= exit_bar_0  < n else ""

            self_._trades_out.append({
                "entry_price":   self_._entry_price,
                "exit_price":    exit_px,
                "pnl":           net_pnl,
                "side":          "long",
                "fees":          total_fees,
                "slippage_cost": 0.0,
                "entry_time":    entry_ts,
                "exit_time":     exit_ts,
                "quantity":      self_._entry_size,
                "pnl_pct":       (exit_px - self_._entry_price) / self_._entry_price,
                "bars_held":     max(exit_bar_0 - entry_bar_0, 0),
                "mae":           min(raw_mae, 0.0),
                "mfe":           max(raw_mfe, 0.0),
            })

        def _record_trade(self_, entry_bar_0: int, exit_bar_0: int, pnlcomm: float) -> None:
            exit_px   = self_._pending_exit_price if self_._pending_exit_price is not None else self_._entry_price
            entry_px  = self_._entry_price
            raw_mae = (self_._min_close - entry_px) / entry_px if entry_px > 0 else 0.0
            raw_mfe = (self_._max_close - entry_px) / entry_px if entry_px > 0 else 0.0

            n = len(datetime_idx)
            entry_ts = str(datetime_idx[entry_bar_0]) if 0 <= entry_bar_0 < n else ""
            exit_ts  = str(datetime_idx[exit_bar_0])  if 0 <= exit_bar_0  < n else ""

            total_fees = self_._entry_commission + self_._pending_exit_commission

            self_._trades_out.append({
                "entry_price":   entry_px,
                "exit_price":    exit_px,
                "pnl":           pnlcomm,
                "side":          "long",
                "fees":          total_fees,
                "slippage_cost": 0.0,
                "entry_time":    entry_ts,
                "exit_time":     exit_ts,
                "quantity":      self_._entry_size,
                "pnl_pct":       (exit_px - entry_px) / entry_px if entry_px > 0 else 0.0,
                "bars_held":     max(exit_bar_0 - entry_bar_0, 0),
                "mae":           min(raw_mae, 0.0),
                "mfe":           max(raw_mfe, 0.0),
            })
            self_._pending_exit_price = None
            self_._pending_exit_commission = 0.0

    return SignalStrategy


# ── Engine ────────────────────────────────────────────────────────────────────

class BacktraderEngine:
    def __init__(self, execution_config: Optional[ExecutionConfig] = None) -> None:
        self._cfg = execution_config or _DEFAULT_CFG

    async def run(
        self,
        strategy_code: str,
        bars: list[OHLCVBar],
    ) -> BacktestResult:
        import backtrader as bt

        valid, errors = validate(strategy_code)
        if not valid:
            raise EngineError("Validation failed: " + "; ".join(errors))

        df = _bars_to_df(bars)

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

        result   = validate_result(raw)
        entries  = result["entries"].reindex(df.index, fill_value=False).astype(bool).values
        exits    = result["exits"].reindex(df.index, fill_value=False).astype(bool).values
        sl_pct   = result.get("stop_loss_pct")
        tp_pct   = result.get("take_profit_pct")

        cerebro = bt.Cerebro()
        cerebro.broker.setcash(100_000.0)
        _apply_commission(cerebro, self._cfg.commission)
        _apply_slippage(cerebro, self._cfg.slippage)

        data_feed = bt.feeds.PandasData(dataname=df, openinterest=-1)
        cerebro.adddata(data_feed)

        StratClass = _make_signal_strategy(entries, exits, sl_pct, tp_pct, df.index)
        cerebro.addstrategy(StratClass)

        loop = asyncio.get_running_loop()
        strats = await loop.run_in_executor(None, cerebro.run)
        strat = strats[0]

        n_bars = len(strat._equity)
        equity_series = pd.Series(
            strat._equity,
            index=df.index[:n_bars],
        )
        trades  = strat._trades_out
        metrics = compute_metrics(equity_series, trades, bars_per_year=_infer_bars_per_year(df))

        return BacktestResult(
            engine="backtrader",
            metrics=metrics,
            trades=list(trades[:500]),
            equity_curve=sample_equity(equity_series),
        )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _bars_to_df(bars: list[OHLCVBar]) -> pd.DataFrame:
    n  = len(bars)
    ts = np.fromiter((b.timestamp for b in bars), dtype="int64",   count=n)
    op = np.fromiter((b.open      for b in bars), dtype="float64", count=n)
    hi = np.fromiter((b.high      for b in bars), dtype="float64", count=n)
    lo = np.fromiter((b.low       for b in bars), dtype="float64", count=n)
    cl = np.fromiter((b.close     for b in bars), dtype="float64", count=n)
    vo = np.fromiter((b.volume    for b in bars), dtype="float64", count=n)
    idx = pd.DatetimeIndex(ts * 1_000_000, dtype="datetime64[ns]")
    return pd.DataFrame(
        {"open": op, "high": hi, "low": lo, "close": cl, "volume": vo},
        index=idx,
    )


def _apply_commission(cerebro, commission_model) -> None:
    import backtrader as bt

    if isinstance(commission_model, PctComm):
        cerebro.broker.setcommission(commission=commission_model.rate)
    elif isinstance(commission_model, PerShareComm):
        cerebro.broker.addcommissioninfo(
            _make_per_share_comminfo(commission_model.per_share, commission_model.min_per_order)
        )
    elif isinstance(commission_model, TieredComm):
        cerebro.broker.addcommissioninfo(_make_tiered_comminfo(commission_model.tiers))
    elif isinstance(commission_model, AShareComm):
        cerebro.broker.addcommissioninfo(
            _make_ashare_comminfo(commission_model.base_rate, commission_model.stamp_rate)
        )


def _apply_slippage(cerebro, slippage_model) -> None:
    if isinstance(slippage_model, FixedBpsSlippage) and slippage_model.bps > 0:
        cerebro.broker.set_slippage_perc(slippage_model.bps / 1e4, slip_match=False)
