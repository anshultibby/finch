"""Add subscription tracking columns to snaptrade_users

Revision ID: 069
Revises: 068
"""
from alembic import op
import sqlalchemy as sa

revision = "069"
down_revision = "068"


def upgrade():
    op.add_column("snaptrade_users", sa.Column("stripe_subscription_id", sa.String(), nullable=True))
    op.add_column("snaptrade_users", sa.Column("subscription_status", sa.String(), nullable=True))
    op.add_column("snaptrade_users", sa.Column("cancel_at_period_end", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("snaptrade_users", sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True))


def downgrade():
    op.drop_column("snaptrade_users", "current_period_end")
    op.drop_column("snaptrade_users", "cancel_at_period_end")
    op.drop_column("snaptrade_users", "subscription_status")
    op.drop_column("snaptrade_users", "stripe_subscription_id")
