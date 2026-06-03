"""Add stale-connection / soft-purge columns to snaptrade_users

Supports the stale-connection reaper: when a SnapTrade-registered user hasn't
logged into Finch (auth.users.last_sign_in_at) for the inactivity threshold, the
reaper de-registers them from SnapTrade (stops the per-user fee) but keeps the
local row + a cached portfolio headline so the UI can show a "reconnect to
refresh" caution. See services/snaptrade_reaper.py.

Revision ID: 075
Revises: 074
"""
from alembic import op
import sqlalchemy as sa

revision = "075"
down_revision = "074"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # When set, the connection was soft-purged (deleted on SnapTrade's side to
    # stop billing) and the user needs to reverify. NULL = active/never purged.
    op.add_column("snaptrade_users", sa.Column("purged_at", sa.DateTime(timezone=True), nullable=True))
    # Last-known portfolio headline captured at purge time, for the caution banner.
    op.add_column("snaptrade_users", sa.Column("last_portfolio_value", sa.Float(), nullable=True))
    op.add_column("snaptrade_users", sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("snaptrade_users", "last_synced_at")
    op.drop_column("snaptrade_users", "last_portfolio_value")
    op.drop_column("snaptrade_users", "purged_at")
