"""drop the dead scheduled_jobs columns

Phase 2 of the automation simplification (see 090). An automation is a time and
an instruction; these three were never part of that:

  priority       — every row was the default 5; only ever broke ties in one ORDER BY
  chat_id        — no caller ever set it; every run now gets a fresh chat
  context_paths  — always []

090 deliberately left them in place so the then-deployed backend kept working.
The new code is live, so they can go. Verified empty of non-default data before
dropping.

Revision ID: 091
Revises: 090
Create Date: 2026-08-06
"""
from alembic import op
import sqlalchemy as sa

revision = '091'
down_revision = '090'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column('scheduled_jobs', 'priority')
    op.drop_column('scheduled_jobs', 'chat_id')
    op.drop_column('scheduled_jobs', 'context_paths')


def downgrade():
    # Restored empty — the dropped values were all defaults.
    op.add_column('scheduled_jobs', sa.Column(
        'context_paths', sa.JSON(), nullable=True))
    op.add_column('scheduled_jobs', sa.Column(
        'chat_id', sa.String(), nullable=True))
    op.add_column('scheduled_jobs', sa.Column(
        'priority', sa.Integer(), nullable=False, server_default='5'))
