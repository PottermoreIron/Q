"""SimpleEngine — thin adapter over _runtime. The golden-file arbiter."""
from __future__ import annotations

from schemas.data import OHLCVBar
from services.engines._runtime import bars_to_df, run_strategy, sample_equity
from services.engines.exceptions import EngineError  # noqa: F401 (re-exported for callers)
from services.engines.protocol import BacktestResult


class SimpleEngine:
    async def run(self, strategy_code: str, bars: list[OHLCVBar]) -> BacktestResult:
        df = bars_to_df(bars)
        metrics, trades, equity = run_strategy(strategy_code, df)
        return BacktestResult(
            engine="simple",
            metrics=metrics,
            trades=list(trades[:500]),
            equity_curve=sample_equity(equity),
        )
