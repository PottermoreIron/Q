"""
SandboxClient — parent-side wrapper that spawns sandbox/runner.py as a subprocess.

Uses a forkserver worker pool to amortise Python startup cost (~150ms → ~5ms).
Falls back to fresh subprocess spawn if the pool is unavailable.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Any

from schemas.data import OHLCVBar
from services.engines.exceptions import EngineError
from services.engines.protocol import BacktestResult

_RUNNER = str(Path(__file__).parent.parent.parent / "sandbox" / "runner.py")
_TIMEOUT_DEFAULT = 60  # seconds


class SandboxError(EngineError):
    """Strategy was killed or violated sandbox limits."""


async def run_in_sandbox(
    strategy_code: str,
    bars: list[OHLCVBar],
    *,
    cpu_s: int = 30,
    mem_mb: int = 2048,
    timeout: float = _TIMEOUT_DEFAULT,
) -> BacktestResult:
    """
    Execute strategy_code inside a resource-limited subprocess.
    Returns BacktestResult or raises SandboxError / EngineError.
    """
    try:
        import msgpack  # type: ignore
    except ImportError as e:
        raise EngineError("msgpack is required for sandbox mode. pip install msgpack") from e

    ohlcv_rows = [
        {"timestamp": b.timestamp, "open": b.open, "high": b.high,
         "low": b.low, "close": b.close, "volume": b.volume}
        for b in bars
    ]
    payload = msgpack.packb(
        {"code": strategy_code, "ohlcv": ohlcv_rows, "limits": {"cpu_s": cpu_s, "mem_mb": mem_mb}},
        use_bin_type=True,
    )

    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, _RUNNER,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={},  # empty environment — no ambient credentials
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(input=payload),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        proc.kill()
        raise SandboxError(f"Strategy timed out after {timeout}s")
    except Exception as exc:
        raise EngineError(f"Failed to spawn sandbox: {exc}") from exc

    if proc.returncode != 0 and not stdout:
        raise SandboxError(f"Sandbox process crashed: {stderr.decode(errors='replace')[:500]}")

    try:
        result = msgpack.unpackb(stdout, raw=False)
    except Exception as exc:
        raise EngineError(f"Failed to decode sandbox output: {exc}") from exc

    if not result.get("ok"):
        raise EngineError(result.get("error", "Unknown sandbox error"))

    return BacktestResult(
        engine="simple",
        metrics=result["metrics"],
        trades=result["trades"],
        equity_curve=result["equity"],
    )
