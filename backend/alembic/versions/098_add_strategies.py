"""add strategies — user-owned playbooks (pillar 5, Phase-0)

A strategy is a named set of trading rules the user adopts and binds to their
goal. Only user-owned rows live here; the starter catalog is code constants
(services/strategy_starters.py). `spec` is the strategy_distiller shape.

Revision ID: 098
Revises: 097
Create Date: 2026-08-30
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "098"
down_revision = "097"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "strategies",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("style", sa.String(), nullable=False, server_default="custom"),
        sa.Column("spec", JSONB(), nullable=True),
        sa.Column("source", sa.String(), nullable=False, server_default="custom"),
        sa.Column("status", sa.String(), nullable=False, server_default="adopted"),
        sa.Column("source_id", sa.String(), nullable=True),
    )
    op.create_index("ix_strategies_user_id", "strategies", ["user_id"])
    op.create_index("ix_strategies_status", "strategies", ["status"])


def downgrade():
    op.drop_index("ix_strategies_status", table_name="strategies")
    op.drop_index("ix_strategies_user_id", table_name="strategies")
    op.drop_table("strategies")
