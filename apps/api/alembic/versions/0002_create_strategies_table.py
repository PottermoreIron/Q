"""create strategies table

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-12
"""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "strategies",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("blocks", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("python_code", sa.Text(), nullable=True),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_strategies_user_id", "strategies", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_strategies_user_id", table_name="strategies")
    op.drop_table("strategies")
