"""create resources table

Revision ID: 006
Revises: 005
Create Date: 2025-10-28
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade():
    # Create resources table
    op.create_table(
        'resources',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('chat_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('tool_name', sa.String(), nullable=False),
        sa.Column('resource_type', sa.String(), nullable=False),  # 'portfolio', 'insider_trades', 'reddit_trends', etc.
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('data', JSONB, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('resource_metadata', JSONB, nullable=True),  # Additional metadata like parameters used
    )
    
    # Add indexes for faster queries
    op.create_index('idx_resources_chat_id', 'resources', ['chat_id'])
    op.create_index('idx_resources_user_id', 'resources', ['user_id'])
    op.create_index('idx_resources_created_at', 'resources', ['created_at'])
    
    # Add resource_id column to chat_messages table
    op.add_column('chat_messages', sa.Column('resource_id', sa.String(), sa.ForeignKey('resources.id', ondelete='SET NULL'), nullable=True))
    op.create_index('idx_chat_messages_resource_id', 'chat_messages', ['resource_id'])


def downgrade():
    op.drop_index('idx_chat_messages_resource_id')
    op.drop_column('chat_messages', 'resource_id')
    op.drop_index('idx_resources_created_at')
    op.drop_index('idx_resources_user_id')
    op.drop_index('idx_resources_chat_id')
    op.drop_table('resources')

