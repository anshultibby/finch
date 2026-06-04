"""drop alpaca tables (alpaca_broker_accounts, alpaca_waitlist)

Removes the Alpaca Broker API integration tables. The Alpaca agent paper-account
and waitlist features were removed in favor of SnapTrade-only portfolio reads.
Also normalizes any vestigial trading_bots rows with platform='alpaca' → 'research'.

Revision ID: 076
Revises: 075
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "076"
down_revision = "075"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Reassign any 'alpaca' platform references to the generic 'research' platform
    # before the Alpaca tables go away. trading_bots stores platform in its config
    # JSONB; bot_positions and trade_logs use a platform column.
    op.execute(
        "UPDATE trading_bots SET config = jsonb_set(config, '{platform}', '\"research\"') "
        "WHERE config->>'platform' = 'alpaca'"
    )
    op.execute("UPDATE bot_positions SET platform = 'research' WHERE platform = 'alpaca'")
    op.execute("UPDATE trade_logs SET platform = 'research' WHERE platform = 'alpaca'")

    op.drop_index("ix_alpaca_broker_accounts_user_id", table_name="alpaca_broker_accounts")
    op.drop_table("alpaca_broker_accounts")

    op.drop_index("ix_alpaca_waitlist_email", table_name="alpaca_waitlist")
    op.drop_table("alpaca_waitlist")


def downgrade() -> None:
    op.create_table(
        "alpaca_waitlist",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_alpaca_waitlist_email", "alpaca_waitlist", ["email"], unique=True)

    op.create_table(
        "alpaca_broker_accounts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False, unique=True),
        sa.Column("alpaca_account_id", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="PENDING"),
        sa.Column("action_required_reason", sa.Text(), nullable=True),
        sa.Column("kyc_snapshot", JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_alpaca_broker_accounts_user_id", "alpaca_broker_accounts", ["user_id"], unique=True)
