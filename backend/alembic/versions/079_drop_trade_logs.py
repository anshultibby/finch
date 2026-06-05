"""drop the unused trade_logs table (dead bot audit-log + half-wired approval flow)

trade_logs (migrations 039/040/046) was never wired up — no routes, no executor
writes, no frontend reads. Its approval-token flow is superseded by the clean,
standalone pending_trades table (078). Dropping it here.

Revision ID: 079
Revises: 078
Create Date: 2026-06-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = '079'
down_revision = '078'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_table('trade_logs')


def downgrade():
    # Recreate the table as it stood after migrations 039 + 040 + 046.
    op.create_table(
        'trade_logs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('bot_id', sa.String(), nullable=False, index=True),
        sa.Column('user_id', sa.String(), nullable=False, index=True),
        sa.Column('execution_id', UUID(as_uuid=True), nullable=True),
        sa.Column('position_id', UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('market', sa.String(), nullable=False),
        sa.Column('market_title', sa.String(), nullable=True),
        sa.Column('platform', sa.String(), nullable=False, server_default='kalshi'),
        sa.Column('side', sa.String(), nullable=True),
        sa.Column('price', sa.Float(), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=True),
        sa.Column('cost_usd', sa.Float(), nullable=True),
        sa.Column('realized_pnl_usd', sa.Float(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='executed', index=True),
        sa.Column('approval_token', sa.String(), nullable=True, index=True),
        sa.Column('approval_method', sa.String(), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('order_response', JSONB(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('dry_run', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('pending_params', JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, index=True),
    )
