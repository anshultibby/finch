"""add system_key to scheduled_jobs (Finch-provisioned default automations)

System jobs (e.g. the nightly day-trading PLAN heartbeat) are provisioned by
Finch, exempt from the per-user recurring limit, exempt from credit charges,
and can be paused but not cancelled. system_key identifies which built-in
automation a row is; (user_id, system_key) is unique so provisioning is
idempotent.

Revision ID: 082
Revises: 081
Create Date: 2026-06-10
"""
from alembic import op
import sqlalchemy as sa

revision = '082'
down_revision = '081'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('scheduled_jobs', sa.Column('system_key', sa.String(), nullable=True))
    op.create_index(
        'uq_scheduled_jobs_user_system_key', 'scheduled_jobs',
        ['user_id', 'system_key'], unique=True,
        postgresql_where=sa.text('system_key IS NOT NULL'),
    )


def downgrade():
    op.drop_index('uq_scheduled_jobs_user_system_key', table_name='scheduled_jobs')
    op.drop_column('scheduled_jobs', 'system_key')
