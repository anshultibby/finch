"""Add scheduled_jobs (agent-scheduled one-off / recurring jobs).

Revision ID: 071
Revises: 070
Create Date: 2026-05-31
"""
from alembic import op
import sqlalchemy as sa


revision = '071'
down_revision = '070'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'scheduled_jobs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('run_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('recurrence', sa.String(), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('chat_id', sa.String(), nullable=True),
        sa.Column('context_paths', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('run_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_scheduled_jobs_user_id', 'scheduled_jobs', ['user_id'])
    op.create_index('ix_scheduled_jobs_run_at', 'scheduled_jobs', ['run_at'])
    op.create_index('ix_scheduled_jobs_status', 'scheduled_jobs', ['status'])


def downgrade() -> None:
    op.drop_index('ix_scheduled_jobs_status', table_name='scheduled_jobs')
    op.drop_index('ix_scheduled_jobs_run_at', table_name='scheduled_jobs')
    op.drop_index('ix_scheduled_jobs_user_id', table_name='scheduled_jobs')
    op.drop_table('scheduled_jobs')
