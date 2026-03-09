"""Create bot_wakeups table.

Revision ID: 038
Revises: 037
Create Date: 2026-03-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '038'
down_revision = '037'
branch_labels = None
depends_on = None


def upgrade() -> None:
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
    )


def downgrade() -> None:
    op.drop_table('bot_wakeups')
