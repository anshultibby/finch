"""Add monitor_note to strategy_positions and allow pending status

Adds:
- monitor_note: text note updated by should_exit() 3-tuple or should_enter()
  returning False; shown in the UI alongside the position card.

The pending status uses the existing String status column — no enum change needed.

Revision ID: 035
Revises: 034
Create Date: 2026-03-03
"""
from alembic import op
import sqlalchemy as sa

revision = '035'
down_revision = '034'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('strategy_positions', sa.Column('monitor_note', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('strategy_positions', 'monitor_note')
