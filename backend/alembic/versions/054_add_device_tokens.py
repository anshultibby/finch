"""add device_tokens table for push notifications

Revision ID: 054
Revises: 053
Create Date: 2026-04-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "054"
down_revision = "053"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "device_tokens",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False, index=True),
        sa.Column("token", sa.String(), nullable=False, unique=True),
        sa.Column("platform", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table("device_tokens")
