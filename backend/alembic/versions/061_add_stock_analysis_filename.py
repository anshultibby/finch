"""Add filename column to stock_analysis for upsert-by-file

Revision ID: 061
Revises: 060
Create Date: 2026-05-14
"""
from alembic import op
import sqlalchemy as sa

revision = "061"
down_revision = "060"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "stock_analysis",
        sa.Column("filename", sa.String(200), nullable=True),
    )
    op.create_unique_constraint(
        "uq_stock_analysis_user_symbol_filename",
        "stock_analysis",
        ["user_id", "symbol", "filename"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_stock_analysis_user_symbol_filename", "stock_analysis")
    op.drop_column("stock_analysis", "filename")
