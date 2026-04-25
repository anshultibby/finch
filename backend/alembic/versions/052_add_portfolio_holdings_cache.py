"""add portfolio_holdings_cache table

Revision ID: 052
Revises: 051
Create Date: 2026-04-25
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = '052'
down_revision = '051'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'portfolio_holdings_cache',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('portfolio_data', JSONB, nullable=False),
        sa.Column('computed_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_portfolio_holdings_cache_user_id', 'portfolio_holdings_cache', ['user_id'], unique=True)


def downgrade():
    op.drop_index('ix_portfolio_holdings_cache_user_id')
    op.drop_table('portfolio_holdings_cache')
