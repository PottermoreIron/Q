"""
Bitemporal OHLCV store model.

Primary key: (symbol, source, timeframe, ts, effective_from)
Append-only: rows are never updated. When upstream data is corrected:
  1. The open row's effective_to is set to fetched_at.
  2. A new row is inserted with the corrected values.

Point-in-time replay: query with effective_from <= as_of < (effective_to OR ∞)
gives byte-identical bars regardless of when the query runs.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Float, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class OHLCVBarRow(Base):
    __tablename__ = "ohlcv_bars"

    # Surrogate PK for ORM convenience; the natural key is the composite below.
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # Natural key components
    symbol:    Mapped[str] = mapped_column(String(50),  nullable=False, index=True)
    source:    Mapped[str] = mapped_column(String(30),  nullable=False)
    timeframe: Mapped[str] = mapped_column(String(10),  nullable=False)
    ts:        Mapped[int] = mapped_column(BigInteger,  nullable=False)

    # OHLCV
    open:      Mapped[float] = mapped_column(Float, nullable=False)
    high:      Mapped[float] = mapped_column(Float, nullable=False)
    low:       Mapped[float] = mapped_column(Float, nullable=False)
    close:     Mapped[float] = mapped_column(Float, nullable=False)
    adj_close: Mapped[float] = mapped_column(Float, nullable=True)
    volume:    Mapped[float] = mapped_column(Float, nullable=False)

    # Bitemporal columns
    fetched_at:     Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    effective_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    effective_to:   Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    __table_args__ = (
        # Covering index for point-in-time range queries
        Index(
            "ix_ohlcv_bars_symbol_source_timeframe_ts",
            "symbol", "source", "timeframe", "ts",
        ),
    )
