"""
Strategy contract — the single return shape that every engine adapter reads from.

A compliant strategy module must expose:

    def run(ohlcv: pd.DataFrame) -> dict:
        return {
            "entries":         pd.Series,        # bool, required
            "exits":           pd.Series,        # bool, required
            "stop_loss_pct":   float | None,     # optional
            "take_profit_pct": float | None,     # optional
            "size_pct":        float | None,     # optional, default 1.0 (full position)
        }

No engine-specific fields are allowed — the adapters handle the translation.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from services.engines.exceptions import EngineError


def validate_result(result: Any, *, source: str = "<strategy>") -> dict:
    """
    Assert that the value returned by run() matches the contract.
    Raises EngineError on violation.
    """
    if not isinstance(result, dict):
        raise EngineError(f"{source}: run() must return a dict, got {type(result).__name__}")

    for required in ("entries", "exits"):
        if required not in result:
            raise EngineError(f"{source}: run() dict is missing required key '{required}'")
        if not isinstance(result[required], pd.Series):
            raise EngineError(
                f"{source}: '{required}' must be a pandas Series, "
                f"got {type(result[required]).__name__}"
            )

    for optional in ("stop_loss_pct", "take_profit_pct", "size_pct"):
        val = result.get(optional)
        if val is not None and not isinstance(val, (int, float)):
            raise EngineError(
                f"{source}: '{optional}' must be a float or None, "
                f"got {type(val).__name__}"
            )

    return result
