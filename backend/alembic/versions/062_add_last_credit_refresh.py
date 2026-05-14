"""Add last_credit_refresh column to snaptrade_users

Revision ID: 062
Revises: 061
Create Date: 2026-05-14
"""
from alembic import op
import sqlalchemy as sa

revision = "062"
down_revision = "061"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "snaptrade_users",
        sa.Column(
            "last_credit_refresh",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("snaptrade_users", "last_credit_refresh")
