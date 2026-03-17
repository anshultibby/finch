"""Add realized_pnl_usd to trade_logs.

Revision ID: 040
Revises: 039
Create Date: 2026-03-10
"""
from alembic import op
import sqlalchemy as sa

revision = '040'
down_revision = '039'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('trade_logs', sa.Column('realized_pnl_usd', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('trade_logs', 'realized_pnl_usd')
