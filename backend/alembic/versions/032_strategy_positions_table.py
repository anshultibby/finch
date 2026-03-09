"""Add strategy_positions table

Tracks open and closed positions entered by strategy code via ctx.enter_position().

Revision ID: 032
Revises: 031
Create Date: 2026-03-02
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = '032'
down_revision = '031'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'strategy_positions',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('strategy_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('market', sa.String(), nullable=False),
        sa.Column('platform', sa.String(), nullable=False),
        sa.Column('side', sa.String(), nullable=False),
        sa.Column('entry_price', sa.Float(), nullable=False),
        sa.Column('entry_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('cost_usd', sa.Float(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='open'),
        sa.Column('exit_config', JSONB(), nullable=False, server_default='{}'),
        sa.Column('entered_via', UUID(as_uuid=True), nullable=True),
        sa.Column('closed_via', UUID(as_uuid=True), nullable=True),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('exit_price', sa.Float(), nullable=True),
        sa.Column('realized_pnl_usd', sa.Float(), nullable=True),
        sa.Column('close_reason', sa.String(), nullable=True),
        sa.Column('current_price', sa.Float(), nullable=True),
        sa.Column('unrealized_pnl_usd', sa.Float(), nullable=True),
        sa.Column('last_priced_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_strategy_positions_strategy_id', 'strategy_positions', ['strategy_id'])
    op.create_index('ix_strategy_positions_user_id', 'strategy_positions', ['user_id'])
    op.create_index('ix_strategy_positions_status', 'strategy_positions', ['status'])


def downgrade() -> None:
    op.drop_index('ix_strategy_positions_status', table_name='strategy_positions')
    op.drop_index('ix_strategy_positions_user_id', table_name='strategy_positions')
    op.drop_index('ix_strategy_positions_strategy_id', table_name='strategy_positions')
    op.drop_table('strategy_positions')
