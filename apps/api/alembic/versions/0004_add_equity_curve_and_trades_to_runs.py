"""add equity_curve and trades columns to backtest_runs

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-12
"""

from alembic import op
import sqlalchemy as sa


revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("backtest_runs", sa.Column("equity_curve", sa.JSON(), nullable=True))
    op.add_column("backtest_runs", sa.Column("trades", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("backtest_runs", "trades")
    op.drop_column("backtest_runs", "equity_curve")
