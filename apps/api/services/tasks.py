"""
Celery tasks for heavy backtest runs.
Each task fetches its own DB session (not injected by FastAPI).
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import settings
from services.celery_app import celery_app
from services.data_ingestion import fetch_binance, fetch_yahoo
from services.simple_engine import EngineError, run_strategy


def _make_session() -> async_sessionmaker:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    return async_sessionmaker(engine, expire_on_commit=False)


@celery_app.task(bind=True, name="tasks.run_backtest")
def run_backtest_task(self, run_id: str) -> None:
    """Heavy backtest task. Updates BacktestRun row directly."""
    asyncio.run(_run_async(self, run_id))


async def _run_async(task, run_id: str) -> None:
    # Import here to avoid circular import at module level
    from models.backtest_run import BacktestRun

    session_factory = _make_session()

    async with session_factory() as db:
        run = await _get_run(db, run_id)
        if not run:
            return

        run.status = "running"
        run.celery_task_id = task.request.id
        await db.commit()

        try:
            cfg = run.data_config
            logs: list[str] = []

            logs.append(f"Fetching {cfg['symbol']} {cfg['timeframe']} data…")
            if cfg["asset_class"] == "crypto":
                bars = await fetch_binance(cfg["symbol"], cfg["timeframe"], cfg["start_date"], cfg["end_date"])
            else:
                bars = await fetch_yahoo(cfg["symbol"], cfg["timeframe"], cfg["start_date"], cfg["end_date"])

            if not bars:
                raise EngineError("No data returned for the given parameters")

            logs.append(f"Loaded {len(bars)} bars. Running strategy…")
            df = _bars_to_df(bars)
            metrics, trades, _equity = run_strategy(run.strategy_code, df)

            run.status = "completed"
            run.engine = "simple"
            run.metrics = metrics
            run.completed_at = datetime.now(timezone.utc)
            run.log_output = "\n".join(logs + [f"Done. {len(trades)} trades."])

        except Exception as exc:
            run.status = "failed"
            run.error_message = str(exc)
            run.completed_at = datetime.now(timezone.utc)

        await db.commit()


async def _get_run(db: AsyncSession, run_id: str):
    from models.backtest_run import BacktestRun
    result = await db.execute(select(BacktestRun).where(BacktestRun.id == run_id))
    return result.scalar_one_or_none()


def _bars_to_df(bars) -> pd.DataFrame:
    rows = [
        {"timestamp": b.timestamp, "open": b.open, "high": b.high,
         "low": b.low, "close": b.close, "volume": b.volume}
        for b in bars
    ]
    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df = df.set_index("timestamp")
    return df
