"""Add skill_files table for multi-file skills

Revision ID: 027
Revises: 026
Create Date: 2026-02-27
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = '027'
down_revision = '026'
branch_labels = None
depends_on = None


def upgrade():
    # Create skill_files table
    op.create_table(
        'skill_files',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('skill_id', sa.String(), nullable=False, index=True),
        sa.Column('filename', sa.String(), nullable=False),  # Relative path within skill dir
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('file_type', sa.String(), nullable=True),   # 'markdown', 'python', 'javascript', etc.
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['skill_id'], ['global_skills.id'], ondelete='CASCADE'),
    )
    
    # Create index for skill_id + filename lookups
    op.create_index('idx_skill_files_skill_filename', 'skill_files', ['skill_id', 'filename'], unique=True)
    
    # Add skill_key column to global_skills for custom lookup keys
    op.add_column('global_skills', sa.Column('skill_key', sa.String(), nullable=True, index=True))
    
    # Add emoji column for UI display
    op.add_column('global_skills', sa.Column('emoji', sa.String(), nullable=True))
    
    # Add homepage column
    op.add_column('global_skills', sa.Column('homepage', sa.String(), nullable=True))


def downgrade():
    # Drop index
    op.drop_index('idx_skill_files_skill_filename', table_name='skill_files')
    
    # Drop table
    op.drop_table('skill_files')
    
    # Drop columns
    op.drop_column('global_skills', 'skill_key')
    op.drop_column('global_skills', 'emoji')
    op.drop_column('global_skills', 'homepage')
