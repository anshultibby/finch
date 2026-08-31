"""add widgets.kind — unified blocks system (widget | cockpit)

The goal cockpit becomes a special widget row (kind="cockpit", one per user,
excluded from lists/gallery). Everything else stays kind="widget".

Revision ID: 099
Revises: 098
Create Date: 2026-08-30
"""
from alembic import op
import sqlalchemy as sa

revision = "099"
down_revision = "098"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("widgets", sa.Column("kind", sa.String(), nullable=False, server_default="widget"))
    op.create_index("ix_widgets_kind", "widgets", ["kind"])


def downgrade():
    op.drop_index("ix_widgets_kind", table_name="widgets")
    op.drop_column("widgets", "kind")
