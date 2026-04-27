"""
Engine routing tests — Task 6.

Covers detect_shape, shape_from_code, and the full registry routing matrix.
Critical cases (must never regress):
  - Explicit hint + missing engine → EngineUnavailable, NOT SimpleEngine fallback
  - Auto-routing falls back silently to SimpleEngine when preferred engine is absent
  - hint takes precedence over shape
"""
from __future__ import annotations

import sys
from unittest.mock import patch

import pytest

from services.engines.exceptions import EngineUnavailable
from services.engines.registry import get_engine
from services.engines.simple import SimpleEngine
from services.engines.vectorbt import VectorBTEngine
from services.engines.backtrader import BacktraderEngine
from services.engines.strategy_shape import detect_shape, shape_from_code


# ── detect_shape ──────────────────────────────────────────────────────────────

def test_detect_shape_no_extras_is_vectorisable():
    assert detect_shape({"entries": None, "exits": None}) == "vectorisable"


def test_detect_shape_stop_loss_present_is_event_driven():
    assert detect_shape({"entries": None, "exits": None, "stop_loss_pct": 0.05}) == "event_driven"


def test_detect_shape_take_profit_present_is_event_driven():
    assert detect_shape({"entries": None, "exits": None, "take_profit_pct": 0.20}) == "event_driven"


def test_detect_shape_size_pct_present_is_event_driven():
    assert detect_shape({"entries": None, "exits": None, "size_pct": 0.5}) == "event_driven"


def test_detect_shape_none_values_do_not_trigger_event_driven():
    d = {"entries": None, "exits": None, "stop_loss_pct": None, "take_profit_pct": None}
    assert detect_shape(d) == "vectorisable"


# ── shape_from_code ───────────────────────────────────────────────────────────

def test_shape_from_code_plain_returns_vectorisable():
    code = "def run(ohlcv):\n    return {'entries': ..., 'exits': ...}"
    assert shape_from_code(code) == "vectorisable"


def test_shape_from_code_with_stop_loss_returns_event_driven():
    code = "def run(ohlcv):\n    return {'entries': ..., 'exits': ..., 'stop_loss_pct': 0.05}"
    assert shape_from_code(code) == "event_driven"


def test_shape_from_code_with_take_profit_returns_event_driven():
    code = "def run(ohlcv):\n    return {'entries': ..., 'exits': ..., 'take_profit_pct': 0.10}"
    assert shape_from_code(code) == "event_driven"


def test_shape_from_code_with_size_pct_returns_event_driven():
    code = "def run(ohlcv):\n    return {'entries': ..., 'exits': ..., 'size_pct': 0.5}"
    assert shape_from_code(code) == "event_driven"


# ── registry: no hint, no shape ───────────────────────────────────────────────

def test_no_hint_no_shape_returns_simple():
    assert isinstance(get_engine(), SimpleEngine)


# ── registry: explicit hint — installed ───────────────────────────────────────

def test_hint_simple_returns_simple():
    assert isinstance(get_engine(hint="simple"), SimpleEngine)


def test_hint_vectorbt_when_installed_returns_vectorbt():
    assert isinstance(get_engine(hint="vectorbt"), VectorBTEngine)


def test_hint_backtrader_when_installed_returns_backtrader():
    assert isinstance(get_engine(hint="backtrader"), BacktraderEngine)


# ── registry: explicit hint — NOT installed → must raise, never fall back ─────

def test_hint_vectorbt_missing_raises_engine_unavailable():
    with patch.dict(sys.modules, {"vectorbt": None}):
        with pytest.raises(EngineUnavailable) as exc_info:
            get_engine(hint="vectorbt")
        assert exc_info.value.engine == "vectorbt"


def test_hint_backtrader_missing_raises_engine_unavailable():
    with patch.dict(sys.modules, {"backtrader": None}):
        with pytest.raises(EngineUnavailable) as exc_info:
            get_engine(hint="backtrader")
        assert exc_info.value.engine == "backtrader"


def test_hint_unknown_raises_engine_unavailable():
    with pytest.raises(EngineUnavailable) as exc_info:
        get_engine(hint="nonexistent_engine")
    assert exc_info.value.engine == "nonexistent_engine"


# ── registry: shape-based auto-routing — installed ───────────────────────────

def test_shape_vectorisable_returns_vectorbt():
    assert isinstance(get_engine(shape="vectorisable"), VectorBTEngine)


def test_shape_event_driven_returns_backtrader():
    assert isinstance(get_engine(shape="event_driven"), BacktraderEngine)


# ── registry: shape-based auto-routing — missing → fallback to Simple (allowed) ─

def test_shape_vectorisable_vectorbt_missing_falls_back_to_simple():
    with patch.dict(sys.modules, {"vectorbt": None}):
        engine = get_engine(shape="vectorisable")
        assert isinstance(engine, SimpleEngine)


def test_shape_event_driven_backtrader_missing_falls_back_to_simple():
    with patch.dict(sys.modules, {"backtrader": None}):
        engine = get_engine(shape="event_driven")
        assert isinstance(engine, SimpleEngine)


# ── registry: hint takes precedence over shape ────────────────────────────────

def test_hint_overrides_shape():
    engine = get_engine(hint="simple", shape="event_driven")
    assert isinstance(engine, SimpleEngine)


def test_hint_backtrader_overrides_vectorisable_shape():
    engine = get_engine(hint="backtrader", shape="vectorisable")
    assert isinstance(engine, BacktraderEngine)


def test_hint_vectorbt_overrides_event_driven_shape():
    engine = get_engine(hint="vectorbt", shape="event_driven")
    assert isinstance(engine, VectorBTEngine)
