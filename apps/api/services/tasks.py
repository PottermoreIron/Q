"""
Celery tasks for heavy backtest runs.
Each task fetches its own DB session (not injected by FastAPI).
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import settings
from services.celery_app import celery_app
from services.data.registry import get_provider
from services.engines.registry import get_engine
from services.engines.strategy_shape import shape_from_code


def _make_session() -> async_sessionmaker:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    return async_sessionmaker(engine, expire_on_commit=False)


@celery_app.task(bind=True, name="tasks.run_backtest")
def run_backtest_task(self, run_id: str) -> None:
    asyncio.run(_run_async(self, run_id))


async def _run_async(task, run_id: str) -> None:
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
            logs: list[str] = [f"Fetching {cfg['symbol']} {cfg['timeframe']} data…"]

            provider = get_provider(cfg.get("source"), cfg["asset_class"])
            bars = await provider.fetch_ohlcv(
                cfg["symbol"], cfg["timeframe"], cfg["start_date"], cfg["end_date"]
            )

            if not bars:
                raise ValueError("No data returned for the given parameters")

            logs.append(f"Loaded {len(bars)} bars. Running strategy…")

            engine = get_engine(
                hint=cfg.get("engine_hint"),
                shape=shape_from_code(run.strategy_code),
            )
            result = await engine.run(run.strategy_code, bars)

            run.status       = "completed"
            run.engine       = result.engine
            run.metrics      = result.metrics
            run.equity_curve = result.equity_curve
            run.trades       = result.trades
            run.completed_at = datetime.now(timezone.utc)
            run.log_output   = "\n".join(
                logs + result.log_lines + [f"Done. {len(result.trades)} trades."]
            )

        except Exception as exc:
            run.status        = "failed"
            run.error_message = str(exc)
            run.completed_at  = datetime.now(timezone.utc)

        await db.commit()


async def _get_run(db: AsyncSession, run_id: str):
    from models.backtest_run import BacktestRun
    result = await db.execute(select(BacktestRun).where(BacktestRun.id == run_id))
    return result.scalar_one_or_none()
