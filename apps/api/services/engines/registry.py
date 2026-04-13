"""
Engine registry.

Routes to the best available engine for the given asset class.
Falls back to SimpleEngine when the preferred engine is not installed or
not yet implemented — no caller needs to handle ImportError or
NotImplementedError.
"""
from __future__ import annotations

from schemas.data import AssetClass
from services.engines.protocol import BacktestEngine
from services.engines.simple import SimpleEngine


def get_engine(asset_class: AssetClass) -> BacktestEngine:
    """
    Return the best available BacktestEngine for the given asset class.

    Routing intent (falls back to SimpleEngine until engines are implemented):
      crypto          → VectorBTEngine   (vectorised, handles crypto conventions)
      stock/forex/    → BacktraderEngine (event-driven, handles splits/dividends)
      futures/options
    """
    if asset_class == "crypto":
        try:
            from services.engines.vectorbt import VectorBTEngine
            engine = VectorBTEngine()
            # Probe that it's actually functional before committing
            engine.run  # noqa: B018
            import vectorbt  # noqa: F401
            return engine
        except (ImportError, NotImplementedError):
            pass

    else:
        try:
            from services.engines.backtrader import BacktraderEngine
            engine = BacktraderEngine()
            import backtrader  # noqa: F401
            return engine
        except (ImportError, NotImplementedError):
            pass

    return SimpleEngine()
