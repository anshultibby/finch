"""add tlh_reminders table

Revision ID: 047
Revises: 046
Create Date: 2026-04-10
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = '047'
down_revision = '046'
branch_labels = None
depends_on = None


def upgrade():
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

    op.create_table(
        'alpaca_waitlist',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(), nullable=False, unique=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_alpaca_waitlist_email', 'alpaca_waitlist', ['email'], unique=True)


def downgrade():
    op.drop_index('ix_alpaca_waitlist_email', table_name='alpaca_waitlist')
    op.drop_table('alpaca_waitlist')
    op.drop_index('ix_tlh_reminders_user_id', table_name='tlh_reminders')
    op.drop_table('tlh_reminders')
