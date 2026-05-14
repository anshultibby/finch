"""Add promo_codes and promo_redemptions tables

Revision ID: 063
Revises: 062
Create Date: 2026-05-14
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "063"
down_revision = "062"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "promo_codes",
        sa.Column("code", sa.String, primary_key=True),
        sa.Column("plan", sa.String, nullable=False, server_default="pro"),
        sa.Column("credits", sa.Integer, nullable=False, server_default="3000"),
        sa.Column("duration_days", sa.Integer, nullable=False, server_default="90"),
        sa.Column("max_uses", sa.Integer, nullable=True),
        sa.Column("times_used", sa.Integer, nullable=False, server_default="0"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "promo_redemptions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.String, nullable=False, index=True),
        sa.Column("code", sa.String, nullable=False),
        sa.Column("plan_granted", sa.String, nullable=False),
        sa.Column("credits_granted", sa.Integer, nullable=False),
        sa.Column("plan_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("promo_redemptions")
    op.drop_table("promo_codes")
