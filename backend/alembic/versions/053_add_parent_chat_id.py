"""add parent_chat_id to chats

Revision ID: 053
Revises: 052
Create Date: 2026-04-26
"""
from alembic import op
import sqlalchemy as sa

revision = "053"
down_revision = "052"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("chats", sa.Column("parent_chat_id", sa.String(), nullable=True))
    op.create_index(op.f("ix_chats_parent_chat_id"), "chats", ["parent_chat_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_chats_parent_chat_id"), table_name="chats")
    op.drop_column("chats", "parent_chat_id")
