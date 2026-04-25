"""
Backtest run router.

POST /backtests          → create run (inline if light, Celery if heavy)
GET  /backtests          → list runs (optionally filtered by strategy_id)
GET  /backtests/{id}     → get run status + results
DELETE /backtests/{id}   → cancel or delete run
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.backtest_run import BacktestRun
from models.strategy import Strategy
from schemas.backtest_run import BacktestRunOut, CreateRunIn, MetricsOut
from services.data.registry import get_provider
from services.engines.exceptions import EngineError
from services.engines.registry import get_engine

router = APIRouter(prefix="/backtests", tags=["backtests"])

# Threshold: ≤ this many bars → run inline; above → Celery
_INLINE_BAR_LIMIT = 1_000
_MAX_TRADES = 500


def _out(r: BacktestRun) -> BacktestRunOut:
    metrics = None
    if r.metrics:
        metrics = MetricsOut(**r.metrics)
    trades_out = None
    if r.trades is not None:
        from schemas.backtest_run import TradeOut
        trades_out = [TradeOut(**t) for t in r.trades]
    return BacktestRunOut(
        id=r.id,
        strategy_id=r.strategy_id,
        strategy_name=r.strategy_name,
        data_config=r.data_config,
        status=r.status,
        engine=r.engine,
        metrics=metrics,
        equity_curve=r.equity_curve,
        trades=trades_out,
        error_message=r.error_message,
        log_output=r.log_output,
        as_of_time=r.as_of_time.isoformat() if r.as_of_time else None,
        created_at=r.created_at.isoformat(),
        completed_at=r.completed_at.isoformat() if r.completed_at else None,
    )


@router.post("", response_model=BacktestRunOut, status_code=status.HTTP_201_CREATED)
async def create_run(body: CreateRunIn, db: AsyncSession = Depends(get_db)) -> BacktestRunOut:
    # Load strategy
    result = await db.execute(select(Strategy).where(Strategy.id == body.strategy_id))
    strategy = result.scalar_one_or_none()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    if not strategy.python_code:
        raise HTTPException(status_code=422, detail="Strategy has no Python code — add blocks or write code first")

    cfg = body.data_config
    run = BacktestRun(
        strategy_id=strategy.id,
        strategy_name=strategy.name,
        strategy_code=strategy.python_code,
        data_config=cfg.model_dump(),
        status="pending",
        as_of_time=datetime.now(timezone.utc),
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    # Fetch data to decide inline vs Celery
    try:
        src = cfg.source if hasattr(cfg, "source") else None
        provider = get_provider(src, cfg.asset_class)
        bars = await provider.fetch_ohlcv(cfg.symbol, cfg.timeframe, cfg.start_date, cfg.end_date)
    except ValueError as exc:
        run.status = "failed"
        run.error_message = str(exc)
        run.completed_at = datetime.now(timezone.utc)
        await db.commit()
        return _out(run)
    except Exception as exc:
        run.status = "failed"
        run.error_message = f"Data fetch failed: {exc}"
        run.completed_at = datetime.now(timezone.utc)
        await db.commit()
        return _out(run)

    if not bars:
        run.status = "failed"
        run.error_message = "No data returned for the given parameters"
        run.completed_at = datetime.now(timezone.utc)
        await db.commit()
        return _out(run)

    if len(bars) <= _INLINE_BAR_LIMIT:
        # ── Inline execution ──────────────────────────────────────────────
        run.status = "running"
        await db.commit()

        try:
            engine = get_engine(cfg.asset_class)
            result = await engine.run(strategy.python_code, bars)

            run.status       = "completed"
            run.engine       = result.engine
            run.metrics      = result.metrics
            run.equity_curve = result.equity_curve
            run.trades       = result.trades
            run.log_output   = f"Ran {len(bars)} bars inline. {len(result.trades)} trades."
            run.completed_at = datetime.now(timezone.utc)

        except (EngineError, Exception) as exc:
            run.status = "failed"
            run.error_message = str(exc)
            run.completed_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(run)
        return _out(run)

    else:
        # ── Celery async execution ────────────────────────────────────────
        try:
            from services.tasks import run_backtest_task
            task = run_backtest_task.delay(run.id)
            run.celery_task_id = task.id
            run.status = "pending"
            await db.commit()
        except Exception:
            # Celery unavailable (dev without worker) — run inline anyway
            run.status = "running"
            await db.commit()
            try:
                engine = get_engine(cfg.asset_class)
                result = await engine.run(strategy.python_code, bars)
                run.status       = "completed"
                run.engine       = result.engine
                run.metrics      = result.metrics
                run.equity_curve = result.equity_curve
                run.trades       = result.trades
                run.log_output   = f"Ran {len(bars)} bars (Celery unavailable, ran inline). {len(result.trades)} trades."
                run.completed_at = datetime.now(timezone.utc)
            except (EngineError, Exception) as exc:
                run.status = "failed"
                run.error_message = str(exc)
                run.completed_at = datetime.now(timezone.utc)
            await db.commit()
            await db.refresh(run)

        return _out(run)


@router.get("", response_model=List[BacktestRunOut])
async def list_runs(
    strategy_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> List[BacktestRunOut]:
    stmt = select(BacktestRun).order_by(BacktestRun.created_at.desc()).limit(limit).offset(offset)
    if strategy_id:
        stmt = stmt.where(BacktestRun.strategy_id == strategy_id)
    result = await db.execute(stmt)
    return [_out(r) for r in result.scalars().all()]


@router.get("/{run_id}", response_model=BacktestRunOut)
async def get_run(run_id: str, db: AsyncSession = Depends(get_db)) -> BacktestRunOut:
    result = await db.execute(select(BacktestRun).where(BacktestRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return _out(run)


@router.delete("/{run_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def cancel_run(run_id: str, db: AsyncSession = Depends(get_db)) -> None:
    result = await db.execute(select(BacktestRun).where(BacktestRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    if run.status in ("pending", "running") and run.celery_task_id:
        try:
            from services.celery_app import celery_app
            celery_app.control.revoke(run.celery_task_id, terminate=True)
        except Exception:
            pass

    await db.delete(run)
    await db.commit()
