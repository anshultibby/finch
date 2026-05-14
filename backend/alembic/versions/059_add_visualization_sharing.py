"""Add sharing support to visualizations

Revision ID: 059
Revises: 058
Create Date: 2025-05-14
"""
from alembic import op
import sqlalchemy as sa

revision = "059"
down_revision = "058"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("visualizations", sa.Column("is_public", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("visualizations", sa.Column("share_token", sa.String(32), nullable=True))
    op.create_index("ix_visualizations_share_token", "visualizations", ["share_token"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_visualizations_share_token", table_name="visualizations")
    op.drop_column("visualizations", "share_token")
    op.drop_column("visualizations", "is_public")
