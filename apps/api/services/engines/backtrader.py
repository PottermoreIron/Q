"""
Backtrader engine — event-driven backtesting for stocks, forex, futures.

Not yet implemented. The stub raises NotImplementedError so the registry
can detect absence and fall back to SimpleEngine cleanly.

Install when ready: pip install backtrader
"""
from __future__ import annotations

from schemas.data import OHLCVBar
from services.engines.protocol import BacktestResult


class BacktraderEngine:
    async def run(
        self,
        strategy_code: str,
        bars: list[OHLCVBar],
    ) -> BacktestResult:
        raise NotImplementedError(
            "Backtrader engine is not yet implemented. "
            "The registry falls back to SimpleEngine automatically."
        )
