"""add tool_cache table for persistent skill/tool response caching

Revision ID: 050
Revises: 049
Create Date: 2026-04-17
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = '050'
down_revision = '049'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'tool_cache',
        sa.Column('cache_key', sa.String(), primary_key=True),
        sa.Column('tool', sa.String(), nullable=False),        # e.g. 'orats', 'fmp', 'polygon'
        sa.Column('endpoint', sa.String(), nullable=False),    # e.g. 'hist/ivrank'
        sa.Column('params', JSONB, nullable=True),             # params used (for debugging)
        sa.Column('data', JSONB, nullable=False),              # cached response
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_tool_cache_tool', 'tool_cache', ['tool'])
    op.create_index('ix_tool_cache_endpoint', 'tool_cache', ['tool', 'endpoint'])


def downgrade():
    op.drop_index('ix_tool_cache_endpoint')
    op.drop_index('ix_tool_cache_tool')
    op.drop_table('tool_cache')
