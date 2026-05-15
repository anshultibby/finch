"""add stripe_customer_id to snaptrade_users

Revision ID: 064
Revises: 063
Create Date: 2026-05-15
"""
from alembic import op
import sqlalchemy as sa

revision = "064"
down_revision = "063"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("snaptrade_users", sa.Column("stripe_customer_id", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("snaptrade_users", "stripe_customer_id")
