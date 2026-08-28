"""add user_goals.preferences — the profile "about me" bag

Extends the user_goals row (the user's mission) into a unified *profile*: one
JSONB column holding the cross-kind preferences the onboarding wizard now
collects (watch topics, notify channel, experience level, constraints, freeform
notes). Kept separate from `config` (which stays kind-specific) and from
UserSettings.preferences (operational job/notification toggles). Additive, no
backfill needed — server_default covers existing rows.

Revision ID: 097
Revises: 096
Create Date: 2026-08-27
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "097"
down_revision = "096"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "user_goals",
        sa.Column("preferences", JSONB(), nullable=False, server_default="{}"),
    )


def downgrade():
    op.drop_column("user_goals", "preferences")
