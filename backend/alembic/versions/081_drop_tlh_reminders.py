"""drop the tlh_reminders table (tax-loss-harvesting feature removed)

The tax-loss-harvesting / swaps feature has been removed from the product.
This drops its tlh_reminders table (created in 047). The unrelated
alpaca_waitlist table from the same migration is left untouched.

Revision ID: 081
Revises: 080
Create Date: 2026-06-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = '081'
down_revision = '080'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_index('ix_tlh_reminders_user_id', table_name='tlh_reminders')
    op.drop_table('tlh_reminders')


def downgrade():
    op.create_table(
        'tlh_reminders',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('symbol_sold', sa.String(), nullable=False),
        sa.Column('symbol_bought', sa.String(), nullable=True),
        sa.Column('loss_amount', sa.Float(), nullable=True),
        sa.Column('sale_date', sa.Date(), nullable=False),
        sa.Column('remind_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('sent', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_tlh_reminders_user_id', 'tlh_reminders', ['user_id'])
