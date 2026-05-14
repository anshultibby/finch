"""add visualizations table for agent-generated HTML dashboards

Revision ID: 057
Revises: 056
Create Date: 2026-05-14
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "057"
down_revision = "056"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "visualizations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.String(), nullable=False, index=True),
        sa.Column("chat_id", sa.String(), sa.ForeignKey("chats.chat_id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(200), nullable=True),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("filename", sa.String(200), nullable=False),
        sa.Column("html_content", sa.Text(), nullable=False),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("tags", JSONB, nullable=True, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "filename", name="uq_viz_user_filename"),
    )


def downgrade():
    op.drop_table("visualizations")
