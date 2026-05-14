"""Add source column to user_watchlist (ai vs manual)

Revision ID: 060
Revises: 059
Create Date: 2026-05-14
"""
from alembic import op
import sqlalchemy as sa

revision = "060"
down_revision = "059"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_watchlist",
        sa.Column("source", sa.String(20), server_default="manual", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("user_watchlist", "source")
