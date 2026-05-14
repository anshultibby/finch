"""add stock_analysis table for AI-generated research notes

Revision ID: 056
Revises: 055
Create Date: 2026-05-13
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "056"
down_revision = "055"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "stock_analysis",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.String(), nullable=False, index=True),
        sa.Column("symbol", sa.String(10), nullable=False, index=True),
        sa.Column("title", sa.String(200), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("chat_id", sa.String(), sa.ForeignKey("chats.chat_id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table("stock_analysis")
