"""Add user_sandboxes table for persistent E2B sandbox IDs

Revision ID: 028
Revises: 027
Create Date: 2026-02-27
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = '028'
down_revision = '027'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'user_sandboxes',
        sa.Column('user_id', sa.String(), primary_key=True),
        sa.Column('sandbox_id', sa.String(), nullable=False),
        sa.Column('skills_loaded', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('skills_hash', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )


def downgrade():
    op.drop_table('user_sandboxes')
