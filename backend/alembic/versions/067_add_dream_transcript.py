"""add transcript column to dreams table

Revision ID: 067
Revises: 066
Create Date: 2026-05-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "067"
down_revision = "066"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("dreams", sa.Column("transcript", JSONB, nullable=True))


def downgrade():
    op.drop_column("dreams", "transcript")
