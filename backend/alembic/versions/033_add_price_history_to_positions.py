"""Add price_history to strategy_positions

Stores a time-series of {t, price} snapshots appended on each monitoring run,
enabling P&L sparklines in the UI.

Revision ID: 033
Revises: 032
Create Date: 2026-03-03
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = '033'
down_revision = '032'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'strategy_positions',
        sa.Column('price_history', JSONB(), nullable=False, server_default='[]'),
    )


def downgrade() -> None:
    op.drop_column('strategy_positions', 'price_history')
