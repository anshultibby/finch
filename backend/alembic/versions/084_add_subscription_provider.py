"""add subscription_provider to user_accounts (stripe | apple)

Tracks which billing system owns a user's Pro grant so web (Stripe) and iOS
(Apple IAP via RevenueCat) only manage the subscription they each own.

Revision ID: 084
Revises: 083
Create Date: 2026-06-13
"""
from alembic import op
import sqlalchemy as sa

revision = '084'
down_revision = '083'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'user_accounts',
        sa.Column('subscription_provider', sa.String(), nullable=True),
    )
    # Backfill existing Pro subscribers — they all came through Stripe.
    op.execute(
        "UPDATE user_accounts SET subscription_provider = 'stripe' "
        "WHERE plan = 'pro' AND stripe_subscription_id IS NOT NULL"
    )


def downgrade():
    op.drop_column('user_accounts', 'subscription_provider')
