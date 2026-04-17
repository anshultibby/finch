"""add user_watchlist table

Revision ID: 049
Revises: 048
Create Date: 2026-04-16
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = '049'
down_revision = '048'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'user_watchlist',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('symbol', sa.String(10), nullable=False),
        sa.Column('added_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('user_id', 'symbol', name='uq_watchlist_user_symbol'),
    )
    op.create_index('ix_user_watchlist_user_id', 'user_watchlist', ['user_id'])


def downgrade():
    op.drop_index('ix_user_watchlist_user_id', table_name='user_watchlist')
    op.drop_table('user_watchlist')
