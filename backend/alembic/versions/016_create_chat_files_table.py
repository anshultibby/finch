"""Create chat_files table

Revision ID: 016
Revises: 015
Create Date: 2025-11-30
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic
revision = '016'
down_revision = '015'
branch_labels = None
depends_on = None


def upgrade():
    # Create chat_files table
    op.create_table(
        'chat_files',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('chat_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('file_type', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('size_bytes', sa.Integer(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('file_metadata', JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('ix_chat_files_chat_id', 'chat_files', ['chat_id'])
    op.create_index('ix_chat_files_user_id', 'chat_files', ['user_id'])
    op.create_index('ix_chat_files_filename', 'chat_files', ['filename'])
    
    # Create unique constraint on (chat_id, filename) - one file per name per chat
    op.create_index(
        'ix_chat_files_chat_filename', 
        'chat_files', 
        ['chat_id', 'filename'],
        unique=True
    )


def downgrade():
    op.drop_index('ix_chat_files_chat_filename', table_name='chat_files')
    op.drop_index('ix_chat_files_filename', table_name='chat_files')
    op.drop_index('ix_chat_files_user_id', table_name='chat_files')
    op.create_index('ix_chat_files_chat_id', 'chat_files', ['chat_id'])
    op.drop_table('chat_files')

