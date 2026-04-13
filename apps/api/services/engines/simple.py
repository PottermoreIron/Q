"""
SimpleEngine — pure-Python backtester, no external engine dependency.

This is the current production engine. It wraps simple_engine.run_strategy,
keeping all pandas/numpy specifics inside this class.
"""
from __future__ import annotations

import pandas as pd

from schemas.data import OHLCVBar
from services.engines.protocol import BacktestResult
from services.simple_engine import EngineError, run_strategy  # noqa: F401 (re-exported)


class SimpleEngine:
    async def run(
        self,
        strategy_code: str,
        bars: list[OHLCVBar],
    ) -> BacktestResult:
        df = _bars_to_df(bars)
        metrics, trades, equity = run_strategy(strategy_code, df)

        return BacktestResult(
            engine="simple",
            metrics=metrics,
            trades=list(trades[:500]),
            equity_curve=_sample_equity(equity),
        )


def _bars_to_df(bars: list[OHLCVBar]) -> pd.DataFrame:
    rows = [
        {"timestamp": b.timestamp, "open": b.open, "high": b.high,
         "low": b.low, "close": b.close, "volume": b.volume}
        for b in bars
    ]
    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df.set_index("timestamp")


def _sample_equity(equity: pd.Series) -> list[list]:
    n = len(equity)
    if n == 0:
        return []
    step = max(1, n // 300)
    sampled = equity.iloc[::step]
    return [[str(idx), float(val)] for idx, val in sampled.items()]
