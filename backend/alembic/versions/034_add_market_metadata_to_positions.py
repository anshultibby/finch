"""Add market_title and event_ticker to strategy_positions

Stores the human-readable market title and Kalshi event_ticker alongside
the raw market ticker, so the UI can show friendly names and correct URLs
without extra API calls.

Revision ID: 034
Revises: 033
Create Date: 2026-03-03
"""
from alembic import op
import sqlalchemy as sa

revision = '034'
down_revision = '033'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('strategy_positions', sa.Column('market_title', sa.String(), nullable=True))
    op.add_column('strategy_positions', sa.Column('event_ticker', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('strategy_positions', 'event_ticker')
    op.drop_column('strategy_positions', 'market_title')
