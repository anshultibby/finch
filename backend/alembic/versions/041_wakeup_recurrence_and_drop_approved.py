"""Add recurrence/message to bot_wakeups, drop approved from trading_bots.

Revision ID: 041
Revises: 040
"""
from alembic import op
import sqlalchemy as sa

revision = "041"
down_revision = "040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add recurrence and message columns to bot_wakeups
    op.add_column("bot_wakeups", sa.Column("recurrence", sa.String(), nullable=True))
    op.add_column("bot_wakeups", sa.Column("message", sa.Text(), nullable=True))

    # Drop approved column from trading_bots
    op.drop_column("trading_bots", "approved")


def downgrade() -> None:
    op.add_column(
        "trading_bots",
        sa.Column("approved", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.drop_column("bot_wakeups", "message")
    op.drop_column("bot_wakeups", "recurrence")
