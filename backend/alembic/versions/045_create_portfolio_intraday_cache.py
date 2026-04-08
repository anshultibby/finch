"""Create portfolio_intraday_cache table.

Revision ID: 045
Revises: 044
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "045"
down_revision = "044"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "portfolio_intraday_cache",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False, index=True),
        sa.Column("account_id", sa.String(), nullable=True),
        sa.Column("days_back", sa.Integer(), nullable=False),
        sa.Column("equity_series", JSONB(), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_portfolio_intraday_cache_lookup",
        "portfolio_intraday_cache",
        ["user_id", "account_id", "days_back"],
    )


def downgrade() -> None:
    op.drop_index("ix_portfolio_intraday_cache_lookup")
    op.drop_table("portfolio_intraday_cache")
