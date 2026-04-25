from __future__ import annotations


class EngineError(Exception):
    """Strategy execution failed (validation, runtime, or logic error)."""


class EngineUnavailable(Exception):
    """Requested engine is not installed. Caller should return HTTP 422."""

    def __init__(self, engine: str, detail: str) -> None:
        self.engine = engine
        super().__init__(
            f"Engine '{engine}' is not available: {detail}. "
            f"Install it with: pip install -e '.[engines]'"
        )
