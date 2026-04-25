"""
Sandbox tests — known escape attempts must be blocked.

Requires msgpack to be installed. Skipped with a clear message if absent.
Tests spawn a real subprocess using the same runner.py the production API uses.
"""

import pytest

try:
    import msgpack  # type: ignore
    HAS_MSGPACK = True
except ImportError:
    HAS_MSGPACK = False


_SKIP = pytest.mark.skipif(not HAS_MSGPACK, reason="msgpack not installed")


def _make_bars(n: int = 50) -> list[dict]:
    base = 1672531200000
    return [
        {"timestamp": base + i * 86400000, "open": 100.0, "high": 105.0,
         "low": 95.0, "close": 100.0, "volume": 1000.0}
        for i in range(n)
    ]


async def _run(code: str, bars=None, *, cpu_s: int = 5, mem_mb: int = 512, timeout: float = 10):
    from schemas.data import OHLCVBar
    from services.engines.sandbox import run_in_sandbox, SandboxError
    from services.engines.exceptions import EngineError

    bar_objs = [OHLCVBar(**b) for b in (bars or _make_bars())]
    return await run_in_sandbox(code, bar_objs, cpu_s=cpu_s, mem_mb=mem_mb, timeout=timeout)


_VALID_STRATEGY = """\
import pandas as pd

def run(ohlcv):
    close = ohlcv["close"]
    entries = pd.Series(False, index=close.index)
    exits   = pd.Series(False, index=close.index)
    entries.iloc[0] = True
    exits.iloc[-2]  = True
    stop_loss_pct   = None
    take_profit_pct = None
    return {"entries": entries, "exits": exits,
            "stop_loss_pct": stop_loss_pct, "take_profit_pct": take_profit_pct}
"""


@_SKIP
@pytest.mark.asyncio
async def test_sandbox_valid_strategy_completes():
    from services.engines.sandbox import run_in_sandbox
    from schemas.data import OHLCVBar

    bars = [OHLCVBar(**b) for b in _make_bars(100)]
    result = await run_in_sandbox(_VALID_STRATEGY, bars, cpu_s=10, mem_mb=512)
    assert result.engine == "simple"
    assert result.metrics is not None


@_SKIP
@pytest.mark.asyncio
async def test_sandbox_blocks_dunder_class():
    """getattr(x, '__class__') must be blocked by the AST validator."""
    from services.engines.sandbox import SandboxError
    from services.engines.exceptions import EngineError

    code = """\
import pandas as pd

def run(ohlcv):
    close = ohlcv["close"]
    _ = getattr(close, "__class__").__bases__
    return {"entries": pd.Series(False, index=close.index),
            "exits": pd.Series(False, index=close.index)}
"""
    with pytest.raises((SandboxError, EngineError)):
        await _run(code)


@_SKIP
@pytest.mark.asyncio
async def test_sandbox_blocks_subclasses():
    """type(...).__subclasses__() must be blocked."""
    from services.engines.sandbox import SandboxError
    from services.engines.exceptions import EngineError

    code = """\
import pandas as pd

def run(ohlcv):
    close = ohlcv["close"]
    _ = type(0).__subclasses__()
    return {"entries": pd.Series(False, index=close.index),
            "exits": pd.Series(False, index=close.index)}
"""
    with pytest.raises((SandboxError, EngineError)):
        await _run(code)


@_SKIP
@pytest.mark.asyncio
async def test_sandbox_blocks_forbidden_import():
    """import os must be blocked by the AST validator."""
    from services.engines.sandbox import SandboxError
    from services.engines.exceptions import EngineError

    code = """\
import os
import pandas as pd

def run(ohlcv):
    return {"entries": pd.Series(False, index=ohlcv["close"].index),
            "exits": pd.Series(False, index=ohlcv["close"].index)}
"""
    with pytest.raises((SandboxError, EngineError)):
        await _run(code)


@_SKIP
@pytest.mark.asyncio
async def test_sandbox_kills_infinite_loop():
    """CPU limit must kill an infinite loop."""
    from services.engines.sandbox import SandboxError
    from services.engines.exceptions import EngineError

    code = """\
import pandas as pd

def run(ohlcv):
    while True:
        pass
    return {"entries": pd.Series(False, index=ohlcv["close"].index),
            "exits": pd.Series(False, index=ohlcv["close"].index)}
"""
    with pytest.raises((SandboxError, EngineError, TimeoutError, Exception)):
        await _run(code, cpu_s=1, timeout=5)


@_SKIP
@pytest.mark.asyncio
async def test_sandbox_kills_memory_bomb():
    """Address-space limit must kill an attempt to allocate 3GB."""
    from services.engines.sandbox import SandboxError
    from services.engines.exceptions import EngineError

    code = """\
import pandas as pd

def run(ohlcv):
    x = bytearray(3 * 1024 ** 3)  # 3 GB
    return {"entries": pd.Series(False, index=ohlcv["close"].index),
            "exits": pd.Series(False, index=ohlcv["close"].index)}
"""
    with pytest.raises((SandboxError, EngineError, MemoryError, Exception)):
        await _run(code, mem_mb=256, timeout=5)
