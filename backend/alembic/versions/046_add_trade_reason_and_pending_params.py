"""add reason and pending_params to trade_logs

Revision ID: 046
Revises: 045
Create Date: 2026-04-07
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = '046'
down_revision = '045'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('trade_logs', sa.Column('reason', sa.Text(), nullable=True))
    op.add_column('trade_logs', sa.Column('pending_params', JSONB(), nullable=True))


def downgrade():
    op.drop_column('trade_logs', 'pending_params')
    op.drop_column('trade_logs', 'reason')
