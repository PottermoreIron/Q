"""
Engine registry.

Routing rules:
  - Explicit hint   → use exactly that engine; raise EngineUnavailable (→ HTTP 422) if missing.
                      Never silently falls back.
  - shape=vectorisable → VectorBTEngine, fallback to SimpleEngine if not installed.
  - shape=event_driven → BacktraderEngine, fallback to SimpleEngine if not installed.
  - No hint, no shape  → SimpleEngine.

Auto-routing may fall back to SimpleEngine; explicit hints may not.
The response always carries `result.engine` so callers can see what actually ran.
"""
from __future__ import annotations

from typing import Optional

from services.engines.exceptions import EngineUnavailable
from services.engines.protocol import BacktestEngine
from services.engines.simple import SimpleEngine

_KNOWN_HINTS = ("simple", "vectorbt", "backtrader")


def get_engine(
    *,
    hint: Optional[str] = None,
    shape: Optional[str] = None,
) -> BacktestEngine:
    if hint is not None:
        if hint not in _KNOWN_HINTS:
            raise EngineUnavailable(hint, f"unknown engine. Valid hints: {', '.join(_KNOWN_HINTS)}")
        if hint == "simple":
            return SimpleEngine()
        if hint == "vectorbt":
            return _require_vectorbt()
        if hint == "backtrader":
            return _require_backtrader()

    if shape == "vectorisable":
        try:
            return _require_vectorbt()
        except EngineUnavailable:
            return SimpleEngine()

    if shape == "event_driven":
        try:
            return _require_backtrader()
        except EngineUnavailable:
            return SimpleEngine()

    return SimpleEngine()


def _require_vectorbt() -> BacktestEngine:
    try:
        import vectorbt  # noqa: F401 — probe; raises ImportError if not installed
        from services.engines.vectorbt import VectorBTEngine
        return VectorBTEngine()
    except ImportError as exc:
        raise EngineUnavailable("vectorbt", str(exc)) from exc


def _require_backtrader() -> BacktestEngine:
    try:
        import backtrader  # noqa: F401 — probe
        from services.engines.backtrader import BacktraderEngine
        return BacktraderEngine()
    except ImportError as exc:
        raise EngineUnavailable("backtrader", str(exc)) from exc
