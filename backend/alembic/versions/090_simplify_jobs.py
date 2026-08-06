"""simplify scheduled_jobs — per-row behaviour flags instead of key sets

An automation is just a time + an instruction. The two behaviours that genuinely
differ per job (is the run comped? does it pause for inactive users?) used to
live in module-level sets keyed on system_key in services/job_scheduler.py.
They're now columns, set once at creation.

ADDITIVE ONLY. The now-unused columns (priority, context_paths, chat_id) stay in
the table so the currently-deployed backend keeps working; they're dropped from
the ORM in this same change and physically removed in a later migration once the
new code is live everywhere.

Revision ID: 090
Revises: 089
Create Date: 2026-08-06
"""
from alembic import op
import sqlalchemy as sa

revision = '090'
down_revision = '089'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('scheduled_jobs', sa.Column(
        'comped', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('scheduled_jobs', sa.Column(
        'activity_gated', sa.Boolean(), nullable=False, server_default=sa.text('false')))

    # Backfill the behaviour the key sets used to encode.
    op.execute("""
        UPDATE scheduled_jobs
           SET comped = true
         WHERE system_key IN ('day_trading_nightly', 'morning_brief')
    """)
    op.execute("""
        UPDATE scheduled_jobs
           SET activity_gated = true
         WHERE system_key IN ('heartbeat', 'heartbeat_trigger')
    """)


def downgrade():
    op.drop_column('scheduled_jobs', 'activity_gated')
    op.drop_column('scheduled_jobs', 'comped')
