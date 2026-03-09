"""Create trade_logs table.

Revision ID: 039
Revises: 038
Create Date: 2026-03-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = '039'
down_revision = '038'
branch_labels = None
depends_on = None


def upgrade() -> None:
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
        sa.Column('status', sa.String(), nullable=False, server_default='executed', index=True),
        sa.Column('approval_token', sa.String(), nullable=True, index=True),
        sa.Column('approval_method', sa.String(), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('order_response', JSONB(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('dry_run', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, index=True),
    )


def downgrade() -> None:
    op.drop_table('trade_logs')
