"""Add cost tracking to scheduled_jobs.

Revision ID: 072
Revises: 071
Create Date: 2026-05-31
"""
from alembic import op
import sqlalchemy as sa

revision = '072'
down_revision = '071'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('scheduled_jobs', sa.Column('last_run_credits', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('scheduled_jobs', sa.Column('credits_spent', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    op.drop_column('scheduled_jobs', 'credits_spent')
    op.drop_column('scheduled_jobs', 'last_run_credits')
