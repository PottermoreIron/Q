"""
Strategy shape detection — determines which engine class is appropriate.

"event_driven" if the strategy returns SL/TP/size_pct (needs an order-loop engine).
"vectorisable" otherwise (VectorBT can handle it efficiently).
"""
from __future__ import annotations

from typing import Literal


def detect_shape(strategy_dict: dict) -> Literal["vectorisable", "event_driven"]:
    """Classify a strategy result dict. Called after executing the strategy."""
    for key in ("stop_loss_pct", "take_profit_pct", "size_pct"):
        if strategy_dict.get(key) is not None:
            return "event_driven"
    return "vectorisable"


def shape_from_code(code: str) -> Literal["vectorisable", "event_driven"]:
    """Fast pre-execution heuristic — scans code text without running it."""
    for key in ("stop_loss_pct", "take_profit_pct", "size_pct"):
        if key in code:
            return "event_driven"
    return "vectorisable"
