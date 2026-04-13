"""
VectorBT engine — vectorised backtesting optimised for crypto and multi-asset quant.

Not yet implemented. The stub raises NotImplementedError so the registry
can detect absence and fall back to SimpleEngine cleanly.

Install when ready: pip install vectorbt
"""
from __future__ import annotations

from schemas.data import OHLCVBar
from services.engines.protocol import BacktestResult


class VectorBTEngine:
    async def run(
        self,
        strategy_code: str,
        bars: list[OHLCVBar],
    ) -> BacktestResult:
        raise NotImplementedError(
            "VectorBT engine is not yet implemented. "
            "The registry falls back to SimpleEngine automatically."
        )
