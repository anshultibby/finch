"""kalshi_bot_trades — trade ledger + candidate observations for the Kalshi bot

One row per trade attempt or per candidate considered (kind discriminates),
per user. Ported from the standalone kalshi-bot/ prototype's SQLite ledger —
see backend/services/kalshi_bot/ for the strategy logic this backs.

Revision ID: 088
Revises: 087
Create Date: 2026-07-14
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = '088'
down_revision = '087'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'kalshi_bot_trades',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.String(), nullable=False, index=True),
        sa.Column('kind', sa.String(), nullable=False),  # trade | observation
        sa.Column('strategy', sa.String(), nullable=False),
        sa.Column('ticker', sa.String(), nullable=False),
        sa.Column('side', sa.String(), nullable=True),        # yes | no (trades only)
        sa.Column('action', sa.String(), nullable=True),      # buy | sell (trades only)
        sa.Column('count', sa.Float(), nullable=True),
        sa.Column('price', sa.Float(), nullable=True),
        sa.Column('dry_run', sa.Boolean(), nullable=True),
        sa.Column('order_id', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),      # simulated | submitted | error
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('settled', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('result', sa.String(), nullable=True),      # yes | no, once settled
        sa.Column('won', sa.Boolean(), nullable=True),
        sa.Column('fee', sa.Float(), nullable=True),
        sa.Column('realized_pnl', sa.Float(), nullable=True),
        sa.Column('detail', JSONB(), nullable=True),          # observation payload
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_kalshi_bot_trades_user_kind', 'kalshi_bot_trades', ['user_id', 'kind'])
    op.create_index('ix_kalshi_bot_trades_settled', 'kalshi_bot_trades', ['settled'])


def downgrade():
    op.drop_index('ix_kalshi_bot_trades_settled', table_name='kalshi_bot_trades')
    op.drop_index('ix_kalshi_bot_trades_user_kind', table_name='kalshi_bot_trades')
    op.drop_table('kalshi_bot_trades')
