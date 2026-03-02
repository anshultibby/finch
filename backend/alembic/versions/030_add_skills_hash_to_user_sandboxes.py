"""Add skills_hash column to user_sandboxes

Revision ID: 030
Revises: 029
Create Date: 2026-02-28
"""
from alembic import op
import sqlalchemy as sa

revision = '030'
down_revision = '029'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('user_sandboxes', sa.Column('skills_hash', sa.String(), nullable=True))


def downgrade():
    op.drop_column('user_sandboxes', 'skills_hash')
