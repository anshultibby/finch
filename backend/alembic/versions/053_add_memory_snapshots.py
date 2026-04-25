"""add memory_snapshots table for cognee memory history

Revision ID: 053
Revises: 052
Create Date: 2026-04-25
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = '053'
down_revision = '052'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'memory_snapshots',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', sa.String(), nullable=False, index=True),
        sa.Column('chat_id', sa.String(), nullable=True, index=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('diff', sa.Text(), nullable=True),
        sa.Column('source', sa.String(50), nullable=False, server_default='cognee'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_memory_snapshots_user_created', 'memory_snapshots', ['user_id', 'created_at'])


def downgrade():
    op.drop_index('ix_memory_snapshots_user_created')
    op.drop_table('memory_snapshots')
