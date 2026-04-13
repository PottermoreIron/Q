"""
BacktestEngine Protocol and BacktestResult type.

Engines receive raw OHLCVBar data and strategy code; they own the
bars-to-DataFrame conversion and every engine-specific detail. Nothing
about vectorbt, backtrader, or any other library leaks past this boundary.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from schemas.data import OHLCVBar


@dataclass
class BacktestResult:
    engine: str
    metrics: dict[str, Any]
    trades: list[dict[str, Any]]
    equity_curve: list[list]      # [[timestamp_str, value], ...]
    log_lines: list[str] = field(default_factory=list)


@runtime_checkable
class BacktestEngine(Protocol):
    async def run(
        self,
        strategy_code: str,
        bars: list[OHLCVBar],
    ) -> BacktestResult: ...
