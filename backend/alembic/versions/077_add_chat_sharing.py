"""add is_public and share_token columns to chats for public sharing

Revision ID: 077
Revises: 076
Create Date: 2026-06-03
"""
from alembic import op
import sqlalchemy as sa

revision = '077'
down_revision = '076'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('chats', sa.Column('is_public', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('chats', sa.Column('share_token', sa.String(length=32), nullable=True))
    op.create_index('ix_chats_share_token', 'chats', ['share_token'], unique=True)


def downgrade():
    op.drop_index('ix_chats_share_token', table_name='chats')
    op.drop_column('chats', 'share_token')
    op.drop_column('chats', 'is_public')
