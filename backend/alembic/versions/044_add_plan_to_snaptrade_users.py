"""Add plan column to snaptrade_users.

Revision ID: 044
Revises: 043
"""
from alembic import op
import sqlalchemy as sa

revision = "044"
down_revision = "043"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "snaptrade_users",
        sa.Column("plan", sa.String(), nullable=False, server_default="free")
    )


def downgrade() -> None:
    op.drop_column("snaptrade_users", "plan")
