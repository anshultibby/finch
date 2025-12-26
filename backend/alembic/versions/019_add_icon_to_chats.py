"""Add icon column to chats table for LLM-generated icons

Revision ID: 019
Revises: efbae5d0ce1e
Create Date: 2025-12-26
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic
revision = '019'
down_revision = 'efbae5d0ce1e'
branch_labels = None
depends_on = None


def upgrade():
    # Add icon column to chats table (emoji icon for chat)
    op.add_column('chats', sa.Column('icon', sa.String(10), nullable=True))


def downgrade():
    op.drop_column('chats', 'icon')

