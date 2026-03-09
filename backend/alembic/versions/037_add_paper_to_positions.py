"""Add paper column to bot_positions.

Revision ID: 037
Revises: 036
Create Date: 2026-03-09
"""
from alembic import op
import sqlalchemy as sa

revision = '037'
down_revision = '036'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('bot_positions', sa.Column('paper', sa.Boolean(), nullable=False, server_default=sa.text('false')))


def downgrade() -> None:
    op.drop_column('bot_positions', 'paper')
