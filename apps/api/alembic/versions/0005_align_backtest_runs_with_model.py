"""Align backtest_runs with current model — add missing columns

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-26
"""

from alembic import op
import sqlalchemy as sa


revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("backtest_runs", sa.Column("engine",          sa.String(20),  nullable=True))
    op.add_column("backtest_runs", sa.Column("celery_task_id",  sa.String(255), nullable=True))
    op.add_column("backtest_runs", sa.Column("metrics",         sa.JSON(),      nullable=True))
    op.add_column("backtest_runs", sa.Column("equity_curve_key",sa.String(255), nullable=True))
    op.add_column("backtest_runs", sa.Column("error_message",   sa.Text(),      nullable=True))
    op.add_column("backtest_runs", sa.Column("log_output",      sa.Text(),      nullable=True))
    op.add_column("backtest_runs", sa.Column(
        "as_of_time",
        sa.DateTime(timezone=True),
        nullable=True,
    ))


def downgrade() -> None:
    op.drop_column("backtest_runs", "as_of_time")
    op.drop_column("backtest_runs", "log_output")
    op.drop_column("backtest_runs", "error_message")
    op.drop_column("backtest_runs", "equity_curve_key")
    op.drop_column("backtest_runs", "metrics")
    op.drop_column("backtest_runs", "celery_task_id")
    op.drop_column("backtest_runs", "engine")
