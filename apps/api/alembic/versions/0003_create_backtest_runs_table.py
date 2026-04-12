"""create backtest_runs table

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-12
"""

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "backtest_runs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("strategy_id", sa.String(), nullable=True),
        sa.Column("strategy_name", sa.String(100), nullable=False),
        sa.Column("strategy_code", sa.Text(), nullable=False),
        sa.Column("data_config", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("engine", sa.String(20), nullable=True),
        sa.Column("celery_task_id", sa.String(255), nullable=True),
        sa.Column("metrics", sa.JSON(), nullable=True),
        sa.Column("equity_curve_key", sa.String(255), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("log_output", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["strategy_id"], ["strategies.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_backtest_runs_strategy_id", "backtest_runs", ["strategy_id"])
    op.create_index("ix_backtest_runs_status", "backtest_runs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_backtest_runs_status", table_name="backtest_runs")
    op.drop_index("ix_backtest_runs_strategy_id", table_name="backtest_runs")
    op.drop_table("backtest_runs")
