"""Simplify skills: drop global_skills/skill_files, replace skills with user_skills

Skills now live on disk at backend/skills/<name>/. The only DB state we need is
which skills each user has enabled.

Revision ID: 029
Revises: 028
Create Date: 2026-02-27
"""
from alembic import op
import sqlalchemy as sa

revision = '029'
down_revision = '028'
branch_labels = None
depends_on = None


def upgrade():
    # Drop in dependency order: skill_files → skills (FK to global_skills) → global_skills
    op.drop_table('skill_files')
    op.drop_table('skills')
    op.drop_table('global_skills')

    # Create the slim user_skills table
    op.create_table(
        'user_skills',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('skill_name', sa.String(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('user_id', 'skill_name', name='uq_user_skills_user_skill'),
    )
    op.create_index('ix_user_skills_user_id', 'user_skills', ['user_id'], unique=False)


def downgrade():
    op.drop_table('user_skills')

    op.create_table(
        'skills',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('source_id', sa.String(), nullable=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        'global_skills',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('author_user_id', sa.String(), nullable=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('skill_key', sa.String(), nullable=True),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('emoji', sa.String(), nullable=True),
        sa.Column('homepage', sa.String(), nullable=True),
        sa.Column('is_official', sa.Boolean(), nullable=False),
        sa.Column('is_system', sa.Boolean(), nullable=False),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('install_count', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        'skill_files',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('skill_id', sa.String(), sa.ForeignKey('global_skills.id', ondelete='CASCADE'), nullable=False),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('file_type', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
