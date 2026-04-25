"""add notify_email column to chats for persistent email notifications

Revision ID: 051
Revises: 050
Create Date: 2026-04-17
"""
from alembic import op
import sqlalchemy as sa

revision = '051'
down_revision = '050'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('chats', sa.Column('notify_email', sa.String(), nullable=True))


def downgrade():
    op.drop_column('chats', 'notify_email')
