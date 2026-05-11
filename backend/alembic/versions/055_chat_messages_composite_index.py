"""add composite index on chat_messages(chat_id, sequence, role) for paginated display queries

Revision ID: 055
Revises: 054
Create Date: 2026-05-10
"""
from alembic import op

revision = "055"
down_revision = "054"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        "ix_chat_messages_chat_seq_role",
        "chat_messages",
        ["chat_id", "sequence", "role"],
    )


def downgrade():
    op.drop_index("ix_chat_messages_chat_seq_role", table_name="chat_messages")
