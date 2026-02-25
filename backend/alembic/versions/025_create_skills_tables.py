"""Create global_skills and skills tables

Revision ID: 025
Revises: 024
Create Date: 2026-02-22

"""
from alembic import op
import sqlalchemy as sa

revision = '025'
down_revision = '024'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'global_skills',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('author_user_id', sa.String(), nullable=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('is_official', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('install_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_global_skills_category', 'global_skills', ['category'])
    op.create_index('idx_global_skills_official', 'global_skills', ['is_official'])

    op.create_table(
        'skills',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('source_id', sa.String(), nullable=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['source_id'], ['global_skills.id'], ondelete='SET NULL')
    )
    op.create_index('idx_skills_user_id', 'skills', ['user_id'])
    op.create_index('idx_skills_user_enabled', 'skills', ['user_id', 'enabled'])
    op.create_index('idx_skills_source_id', 'skills', ['source_id'])


def downgrade() -> None:
    op.drop_index('idx_skills_source_id', table_name='skills')
    op.drop_index('idx_skills_user_enabled', table_name='skills')
    op.drop_index('idx_skills_user_id', table_name='skills')
    op.drop_table('skills')

    op.drop_index('idx_global_skills_official', table_name='global_skills')
    op.drop_index('idx_global_skills_category', table_name='global_skills')
    op.drop_table('global_skills')
