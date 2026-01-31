"""add chat processing status

Revision ID: 024
Revises: 023
Create Date: 2026-01-26

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '024'
down_revision = '023'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add processing status columns to chats table for stream reconnection support.
    
    These columns track whether a chat is currently being processed, enabling
    smart reconnection when users navigate away and come back.
    """
    # Add is_processing column (defaults to False)
    op.add_column('chats', sa.Column('is_processing', sa.Boolean(), nullable=False, server_default='false'))
    
    # Add processing_started_at timestamp column (nullable)
    op.add_column('chats', sa.Column('processing_started_at', sa.DateTime(timezone=True), nullable=True))
    
    # Add index on is_processing for fast lookups
    op.create_index('ix_chats_is_processing', 'chats', ['is_processing'])


def downgrade():
    """Remove processing status columns from chats table"""
    op.drop_index('ix_chats_is_processing', table_name='chats')
    op.drop_column('chats', 'processing_started_at')
    op.drop_column('chats', 'is_processing')
