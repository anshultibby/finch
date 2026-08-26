"""add user_goals — the user's active goal / "mission"

Backs the goal-oriented cockpit + onboarding wizard. One row per user (keyed by
the Supabase auth user id). The goal shape is selected by `kind`
(number | grow | income | protect); shape-specific extras live in the JSONB
`config` column so new goal types don't churn the schema.

Revision ID: 096
Revises: 095
Create Date: 2026-08-25
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "096"
down_revision = "095"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "user_goals",
        sa.Column("user_id", sa.String(), primary_key=True),
        sa.Column("kind", sa.String(), nullable=False, server_default="number"),
        sa.Column("title", sa.String(), nullable=False, server_default=""),
        sa.Column("objective", sa.Text(), nullable=True),
        sa.Column("target_amount", sa.Float(), nullable=True),
        sa.Column("deadline", sa.Date(), nullable=True),
        sa.Column("horizon_years", sa.Integer(), nullable=True),
        sa.Column("monthly_contribution", sa.Float(), nullable=True),
        sa.Column("monthly_income", sa.Float(), nullable=True),
        sa.Column("risk", sa.Integer(), nullable=True),
        sa.Column("options_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("config", JSONB(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_user_goals_user_id", "user_goals", ["user_id"])


def downgrade():
    op.drop_index("ix_user_goals_user_id", table_name="user_goals")
    op.drop_table("user_goals")
