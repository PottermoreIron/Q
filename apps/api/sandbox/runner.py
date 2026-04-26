"""
Sandbox runner — spawned as a subprocess by SandboxClient.

Protocol: reads one msgpack message from stdin:
    {"code": str, "ohlcv": list[dict], "limits": {"cpu_s": int, "mem_mb": int}}

Writes one msgpack message to stdout:
    {"ok": True,  "metrics": dict, "trades": list, "equity": list}  on success
    {"ok": False, "error": str}                                       on failure

Spawned with env={} so no ambient credentials are available.
setrlimit enforces CPU and address-space limits before any user code runs.
"""

from __future__ import annotations

import os
import resource
import sys


def _apply_limits(cpu_s: int, mem_mb: int) -> None:
    def _set(res, soft, hard=None):
        _, cur_hard = resource.getrlimit(res)
        new_hard = min(hard or cur_hard, cur_hard) if cur_hard != resource.RLIM_INFINITY else (hard or resource.RLIM_INFINITY)
        new_soft = min(soft, new_hard) if new_hard != resource.RLIM_INFINITY else soft
        try:
            resource.setrlimit(res, (new_soft, new_hard))
        except (ValueError, resource.error):
            pass  # macOS: can't raise above OS hard limit; skip silently

    _set(resource.RLIMIT_CPU, cpu_s, cpu_s)

    mem_bytes = mem_mb * 1024 * 1024
    _set(resource.RLIMIT_AS, mem_bytes, mem_bytes)

    _set(resource.RLIMIT_NOFILE, 16, 16)


def _run() -> None:
    import msgpack  # type: ignore

    raw = sys.stdin.buffer.read()
    req = msgpack.unpackb(raw, raw=False)

    limits = req.get("limits", {})
    _apply_limits(
        cpu_s=int(limits.get("cpu_s", 30)),
        mem_mb=int(limits.get("mem_mb", 2048)),
    )

    try:
        _execute(req["code"], req["ohlcv"])
    except Exception as exc:
        out = msgpack.packb({"ok": False, "error": str(exc)}, use_bin_type=True)
        sys.stdout.buffer.write(out)
        sys.stdout.buffer.flush()
        sys.exit(0)


def _execute(code: str, ohlcv_rows: list[dict]) -> None:
    import math

    import msgpack  # type: ignore
    import numpy as np
    import pandas as pd

    # Re-run AST validator as first wall
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from services.python_validator import validate
    from services.engines._runtime import _simulate, _infer_bars_per_year, _default_execution_config
    from services.metrics import compute_metrics

    valid, errors = validate(code)
    if not valid:
        raise ValueError("Validation failed: " + "; ".join(errors))

    # Reconstruct DataFrame
    df = pd.DataFrame(ohlcv_rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df = df.set_index("timestamp")

    import builtins as _builtins_mod
    _real_import = _builtins_mod.__import__
    _ALLOWED = {"numpy", "pandas", "math", "np", "pd"}

    def _safe_import(name, *args, **kwargs):
        if name.split(".")[0] not in _ALLOWED:
            raise ImportError(f"import '{name}' is not allowed in strategy code")
        return _real_import(name, *args, **kwargs)

    exec_globals = {
        "__builtins__": {"__import__": _safe_import, "len": len, "range": range,
                         "enumerate": enumerate, "zip": zip, "map": map,
                         "filter": filter, "sorted": sorted, "list": list,
                         "dict": dict, "set": set, "tuple": tuple,
                         "int": int, "float": float, "str": str, "bool": bool,
                         "max": max, "min": min, "sum": sum, "abs": abs,
                         "round": round, "any": any, "all": all,
                         "isinstance": isinstance, "print": lambda *_: None,
                         "None": None, "True": True, "False": False},
        "np": np, "numpy": np,
        "pd": pd, "pandas": pd,
        "math": math,
    }
    exec(compile(code, "<strategy>", "exec"), exec_globals)  # noqa: S102

    run_fn = exec_globals.get("run")
    if not callable(run_fn):
        raise ValueError("run() function not found after execution")

    raw = run_fn(df.copy())
    if not isinstance(raw, dict) or "entries" not in raw or "exits" not in raw:
        raise ValueError("run() must return a dict with 'entries' and 'exits' keys")

    entries = raw["entries"].reindex(df.index, fill_value=False).astype(bool)
    exits   = raw["exits"].reindex(df.index, fill_value=False).astype(bool)

    equity, trades = _simulate(df, entries, exits, 100_000.0, _default_execution_config())
    bpy = _infer_bars_per_year(df)
    metrics = compute_metrics(equity, trades, bars_per_year=bpy)

    n = len(equity)
    step = max(1, n // 300)
    eq_samples = [[str(idx), float(val)] for idx, val in equity.iloc[::step].items()]

    out = msgpack.packb(
        {"ok": True, "metrics": metrics, "trades": trades[:500], "equity": eq_samples},
        use_bin_type=True,
    )
    sys.stdout.buffer.write(out)
    sys.stdout.buffer.flush()


if __name__ == "__main__":
    _run()
