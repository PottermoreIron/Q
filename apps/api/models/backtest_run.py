import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class BacktestRun(Base):
    __tablename__ = "backtest_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    strategy_id: Mapped[str] = mapped_column(
        String, ForeignKey("strategies.id", ondelete="SET NULL"), nullable=True, index=True
    )
    strategy_name: Mapped[str] = mapped_column(String(100), nullable=False)
    strategy_code: Mapped[str] = mapped_column(Text, nullable=False)
    data_config: Mapped[dict] = mapped_column(JSON, nullable=False)

    # job state
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    # pending | running | completed | failed | cancelled
    engine: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    # simple | vectorbt | backtrader
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # results (nullable until completed)
    metrics: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # sampled equity curve: list of [iso_timestamp, value] pairs, max 300 points
    equity_curve: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    # trade list: list of {entry_price, exit_price, pnl, side}, max 500 trades
    trades: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    equity_curve_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    log_output: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # as_of_time: the bitemporal anchor — data read for this run used bars where
    # effective_from <= as_of_time.  Replay with the same value gives byte-identical results.
    as_of_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
