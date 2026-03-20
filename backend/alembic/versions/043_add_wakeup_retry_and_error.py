"""Add retry_count and error columns to bot_wakeups.

Revision ID: 043
Revises: 042
"""
from alembic import op
import sqlalchemy as sa

revision = "043"
down_revision = "042"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("bot_wakeups", sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("bot_wakeups", sa.Column("error", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("bot_wakeups", "error")
    op.drop_column("bot_wakeups", "retry_count")
