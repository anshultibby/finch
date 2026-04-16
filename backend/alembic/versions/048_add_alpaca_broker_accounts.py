"""add alpaca_broker_accounts table

Revision ID: 048
Revises: 047
Create Date: 2026-04-16
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = '048'
down_revision = '047'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'alpaca_broker_accounts',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', sa.String(), nullable=False, unique=True),
        sa.Column('alpaca_account_id', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='PENDING'),
        sa.Column('action_required_reason', sa.Text(), nullable=True),
        sa.Column('kyc_snapshot', JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_alpaca_broker_accounts_user_id', 'alpaca_broker_accounts', ['user_id'], unique=True)


def downgrade():
    op.drop_index('ix_alpaca_broker_accounts_user_id', table_name='alpaca_broker_accounts')
    op.drop_table('alpaca_broker_accounts')
