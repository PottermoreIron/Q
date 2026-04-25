"""
Compiles a list of strategy blocks into a runnable Python function.

The generated code targets VectorBT for crypto/quant strategies and
Backtrader for stocks/forex. Phase 3 generates VectorBT-style code;
the Backtrader adapter comes in Phase 4.

Generated function signature:
    def run(ohlcv: pd.DataFrame) -> dict:
        # returns {'entries': pd.Series[bool], 'exits': pd.Series[bool]}
"""

from __future__ import annotations

from textwrap import dedent
from typing import Any, Dict, List

HEADER = dedent("""\
    import numpy as np
    import pandas as pd

    def run(ohlcv: pd.DataFrame) -> dict:
        \"\"\"
        Strategy entry/exit signals.
        ohlcv columns: open, high, low, close, volume
        Returns: dict with 'entries' and 'exits' boolean Series.
        \"\"\"
        close = ohlcv["close"]
        high  = ohlcv["high"]
        low   = ohlcv["low"]

""")

FOOTER = dedent("""\

        return {
            "entries":         entries,
            "exits":           exits,
            "stop_loss_pct":   stop_loss_pct,
            "take_profit_pct": take_profit_pct,
        }
""")


def _indent(code: str, spaces: int = 4) -> str:
    pad = " " * spaces
    return "\n".join(pad + line if line.strip() else line for line in code.splitlines())


def _compile_indicator(name: str, params: Dict[str, Any]) -> str:
    """Returns a Python snippet declaring the indicator variable."""
    p = params
    if name == "ema":
        period = int(p.get("period", 20))
        var = f"ema_{period}"
        return f'{var} = close.ewm(span={period}, adjust=False).mean()'
    if name == "sma":
        period = int(p.get("period", 50))
        var = f"sma_{period}"
        return f'{var} = close.rolling({period}).mean()'
    if name == "rsi":
        period = int(p.get("period", 14))
        var = f"rsi_{period}"
        return dedent(f"""\
            _delta_{period} = close.diff()
            _gain_{period}  = _delta_{period}.clip(lower=0).rolling({period}).mean()
            _loss_{period}  = (-_delta_{period}).clip(lower=0).rolling({period}).mean()
            {var} = 100 - (100 / (1 + _gain_{period} / _loss_{period}.replace(0, 1e-10)))""")
    if name == "macd":
        fast   = int(p.get("fast", 12))
        slow   = int(p.get("slow", 26))
        signal = int(p.get("signal", 9))
        return dedent(f"""\
            _macd_line   = close.ewm(span={fast}, adjust=False).mean() - close.ewm(span={slow}, adjust=False).mean()
            _macd_signal = _macd_line.ewm(span={signal}, adjust=False).mean()
            macd_hist    = _macd_line - _macd_signal""")
    if name == "bbands":
        period  = int(p.get("period", 20))
        std_dev = float(p.get("std_dev", 2.0))
        return dedent(f"""\
            _bb_mid   = close.rolling({period}).mean()
            _bb_std   = close.rolling({period}).std()
            bb_upper  = _bb_mid + {std_dev} * _bb_std
            bb_lower  = _bb_mid - {std_dev} * _bb_std
            bb_mid    = _bb_mid""")
    if name == "atr":
        period = int(p.get("period", 14))
        return dedent(f"""\
            _tr_{period} = pd.concat([
                high - low,
                (high - close.shift()).abs(),
                (low  - close.shift()).abs(),
            ], axis=1).max(axis=1)
            atr_{period} = _tr_{period}.rolling({period}).mean()""")
    return f"# Unknown indicator: {name}"


def _compile_condition(name: str, params: Dict[str, Any]) -> tuple[str, str]:
    """Returns (entry_signal_code, exit_signal_code)."""
    p = params
    if name == "ema_crossover":
        fast = int(p.get("fast_period", 10))
        slow = int(p.get("slow_period", 30))
        entry = f"ema_{fast} > ema_{slow}"
        exit_ = f"ema_{fast} < ema_{slow}"
        return entry, exit_
    if name == "sma_crossover":
        fast = int(p.get("fast_period", 20))
        slow = int(p.get("slow_period", 50))
        return f"sma_{fast} > sma_{slow}", f"sma_{fast} < sma_{slow}"
    if name == "rsi_mean_reversion":
        period    = int(p.get("period", 14))
        oversold  = float(p.get("oversold", 30))
        overbought = float(p.get("overbought", 70))
        return f"rsi_{period} < {oversold}", f"rsi_{period} > {overbought}"
    if name == "macd_crossover":
        return "macd_hist > 0", "macd_hist < 0"
    if name == "bollinger_breakout":
        return "close > bb_upper", "close < bb_mid"
    if name == "bollinger_mean_reversion":
        return "close < bb_lower", "close > bb_mid"
    if name == "price_above_sma":
        period = int(p.get("period", 200))
        return f"close > sma_{period}", f"close < sma_{period}"
    return "pd.Series(False, index=close.index)", "pd.Series(False, index=close.index)"


def compile_blocks(blocks: List[Dict[str, Any]]) -> str:
    """Compile strategy blocks into a Python function string."""
    if not blocks:
        return _empty_strategy()

    indicator_lines: List[str] = []
    entry_exprs:     List[str] = []
    exit_exprs:      List[str] = []
    stop_loss_pct:   float | None = None
    take_profit_pct: float | None = None

    for block in blocks:
        btype = block.get("type", "")
        name  = block.get("name", "")
        params = block.get("params", {})

        if btype == "indicator":
            indicator_lines.append(_compile_indicator(name, params))

        elif btype == "condition":
            entry, exit_ = _compile_condition(name, params)
            entry_exprs.append(entry)
            exit_exprs.append(exit_)

        elif btype == "action":
            if name == "stop_loss":
                stop_loss_pct = float(params.get("percent", 5))
            elif name == "take_profit":
                take_profit_pct = float(params.get("percent", 10))

    # Build body
    body_lines: List[str] = []

    if indicator_lines:
        body_lines.append("# --- Indicators ---")
        for line in indicator_lines:
            body_lines.append(line)
        body_lines.append("")

    body_lines.append("# --- Signals ---")
    if entry_exprs:
        combined_entry = " & ".join(f"({e})" for e in entry_exprs)
        body_lines.append(f"entries = {combined_entry}")
    else:
        body_lines.append("entries = pd.Series(False, index=close.index)")

    if exit_exprs:
        combined_exit = " | ".join(f"({e})" for e in exit_exprs)
        body_lines.append(f"exits   = {combined_exit}")
    else:
        body_lines.append("exits   = pd.Series(False, index=close.index)")

    body_lines.append("")
    body_lines.append("# --- Risk management (applied by the engine) ---")
    body_lines.append(f"stop_loss_pct   = {stop_loss_pct!r}")
    body_lines.append(f"take_profit_pct = {take_profit_pct!r}")

    body = "\n".join(_indent(line) if line else "" for line in body_lines)

    result = HEADER + body + FOOTER

    # Clean up blank lines > 2 consecutive
    import re
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result


def _empty_strategy() -> str:
    return dedent("""\
        import numpy as np
        import pandas as pd

        def run(ohlcv: pd.DataFrame) -> dict:
            \"\"\"
            Define your strategy by adding blocks or writing code directly.
            ohlcv columns: open, high, low, close, volume
            \"\"\"
            close = ohlcv["close"]

            # Add indicators and conditions using the block panel,
            # or write your strategy logic here directly.
            entries = pd.Series(False, index=close.index)
            exits   = pd.Series(False, index=close.index)

            stop_loss_pct   = None
            take_profit_pct = None

            return {
                "entries":         entries,
                "exits":           exits,
                "stop_loss_pct":   stop_loss_pct,
                "take_profit_pct": take_profit_pct,
            }
    """)
