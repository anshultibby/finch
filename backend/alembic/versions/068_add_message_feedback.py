"""add message_feedback table

Revision ID: 068
Revises: 067
Create Date: 2026-05-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "068"
down_revision = "067"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "message_feedback",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("chat_id", sa.String, nullable=False, index=True),
        sa.Column("user_id", sa.String, nullable=False, index=True),
        sa.Column("message_index", sa.Integer, nullable=False),
        sa.Column("feedback_type", sa.String, nullable=False),  # 'like' or 'dislike'
        sa.Column("comment", sa.Text, nullable=True),
        sa.Column("message_content", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("message_feedback")
