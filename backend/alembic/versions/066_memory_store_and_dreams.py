"""add store_files and dreams tables

Revision ID: 066
Revises: 065
Create Date: 2026-05-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "066"
down_revision = "065"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "store_files",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.String(), nullable=False, index=True),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("file_type", sa.String(), nullable=False, server_default="store"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "dreams",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.String(), nullable=False, index=True),
        sa.Column("status", sa.String(), nullable=False, index=True),
        sa.Column("trigger", sa.String(), nullable=False),
        sa.Column("chat_ids", JSONB, nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("self_score", sa.Integer(), nullable=True),
        sa.Column("output_diff", JSONB, nullable=True),
        sa.Column("follow_ups", JSONB, nullable=True),
        sa.Column("token_usage", JSONB, nullable=True),
        sa.Column("transcript", JSONB, nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table("dreams")
    op.drop_table("store_files")
