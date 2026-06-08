"""drop the legacy trading-bots subsystem

The trading_bots subsystem (migrations 036-043) is superseded by the
scheduled-jobs / automations feature (071) + pending_trades approval flow (078).
Its frontend was already removed and its backend was orphaned (no registered
routes). Dropping the tables and the unused chats.bot_id column here.

Revision ID: 080
Revises: 079
Create Date: 2026-06-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = '080'
down_revision = '079'
branch_labels = None
depends_on = None


def upgrade():
    # Drop children first (FK -> trading_bots ON DELETE CASCADE), then parent.
    op.drop_table('bot_wakeups')
    op.drop_table('bot_positions')
    op.drop_table('bot_executions')
    op.drop_table('bot_files')
    op.drop_table('trading_bots')
    # Postgres drops the column's index along with the column.
    op.drop_column('chats', 'bot_id')


def downgrade():
    op.add_column('chats', sa.Column('bot_id', sa.String(), nullable=True))
    op.create_index('ix_chats_bot_id', 'chats', ['bot_id'])

    op.create_table(
        'trading_bots',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('user_id', sa.String(), nullable=False, index=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('icon', sa.String(length=10), nullable=True),
        sa.Column('directory', sa.String(), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.false(), index=True),
        sa.Column('config', JSONB(), nullable=False, server_default='{}'),
        sa.Column('stats', JSONB(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        'bot_files',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('bot_id', sa.String(), sa.ForeignKey('trading_bots.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('file_type', sa.String(), nullable=False, server_default='code'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        'bot_executions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('bot_id', sa.String(), sa.ForeignKey('trading_bots.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('user_id', sa.String(), nullable=False, index=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('data', JSONB(), nullable=False, server_default='{}'),
    )

    op.create_table(
        'bot_positions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('bot_id', sa.String(), sa.ForeignKey('trading_bots.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('user_id', sa.String(), nullable=False, index=True),
        sa.Column('market', sa.String(), nullable=False),
        sa.Column('platform', sa.String(), nullable=False),
        sa.Column('side', sa.String(), nullable=False),
        sa.Column('market_title', sa.String(), nullable=True),
        sa.Column('event_ticker', sa.String(), nullable=True),
        sa.Column('entry_price', sa.Float(), nullable=False),
        sa.Column('entry_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('cost_usd', sa.Float(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='open', index=True),
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
        sa.Column('price_history', JSONB(), nullable=False, server_default='[]'),
        sa.Column('monitor_note', sa.Text(), nullable=True),
        sa.Column('paper', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        'bot_wakeups',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('bot_id', sa.String(), nullable=False, index=True),
        sa.Column('user_id', sa.String(), nullable=False, index=True),
        sa.Column('trigger_at', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('trigger_type', sa.String(), nullable=False, server_default='custom'),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('context', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('status', sa.String(), nullable=False, server_default='pending', index=True),
        sa.Column('chat_id', sa.String(), nullable=True),
        sa.Column('triggered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('recurrence', sa.String(), nullable=True),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error', sa.Text(), nullable=True),
    )
