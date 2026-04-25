"""Create ohlcv_bars table (bitemporal OHLCV store)

Revision ID: 0006
Revises: 0005
Create Date: 2026-04-26
"""

from alembic import op
import sqlalchemy as sa


revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ohlcv_bars",
        sa.Column("id",             sa.String(),                   primary_key=True),
        sa.Column("symbol",         sa.String(50),                 nullable=False),
        sa.Column("source",         sa.String(30),                 nullable=False),
        sa.Column("timeframe",      sa.String(10),                 nullable=False),
        sa.Column("ts",             sa.BigInteger(),               nullable=False),
        sa.Column("open",           sa.Float(),                    nullable=False),
        sa.Column("high",           sa.Float(),                    nullable=False),
        sa.Column("low",            sa.Float(),                    nullable=False),
        sa.Column("close",          sa.Float(),                    nullable=False),
        sa.Column("adj_close",      sa.Float(),                    nullable=True),
        sa.Column("volume",         sa.Float(),                    nullable=False),
        sa.Column("fetched_at",     sa.DateTime(timezone=True),
                  server_default=sa.text("now()"),                 nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"),                 nullable=False),
        sa.Column("effective_to",   sa.DateTime(timezone=True),    nullable=True),
    )
    op.create_index("ix_ohlcv_bars_symbol",         "ohlcv_bars", ["symbol"])
    op.create_index("ix_ohlcv_bars_effective_from", "ohlcv_bars", ["effective_from"])
    op.create_index("ix_ohlcv_bars_effective_to",   "ohlcv_bars", ["effective_to"])
    op.create_index(
        "ix_ohlcv_bars_symbol_source_timeframe_ts",
        "ohlcv_bars", ["symbol", "source", "timeframe", "ts"],
    )


def downgrade() -> None:
    op.drop_index("ix_ohlcv_bars_symbol_source_timeframe_ts", "ohlcv_bars")
    op.drop_index("ix_ohlcv_bars_effective_to",   "ohlcv_bars")
    op.drop_index("ix_ohlcv_bars_effective_from", "ohlcv_bars")
    op.drop_index("ix_ohlcv_bars_symbol",         "ohlcv_bars")
    op.drop_table("ohlcv_bars")
