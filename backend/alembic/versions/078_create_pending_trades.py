"""create pending_trades table for one-click email trade approval

Revision ID: 078
Revises: 077
Create Date: 2026-06-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = '078'
down_revision = '077'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'pending_trades',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('token', sa.String(length=64), nullable=False),
        sa.Column('broker', sa.String(), server_default='robinhood', nullable=False),
        sa.Column('account_number', sa.String(), nullable=False),
        sa.Column('order_params', JSONB(), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('status', sa.String(), server_default='pending', nullable=False),
        sa.Column('order_response', JSONB(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_pending_trades_user_id', 'pending_trades', ['user_id'])
    op.create_index('ix_pending_trades_token', 'pending_trades', ['token'], unique=True)
    op.create_index('ix_pending_trades_status', 'pending_trades', ['status'])


def downgrade():
    op.drop_index('ix_pending_trades_status', table_name='pending_trades')
    op.drop_index('ix_pending_trades_token', table_name='pending_trades')
    op.drop_index('ix_pending_trades_user_id', table_name='pending_trades')
    op.drop_table('pending_trades')
