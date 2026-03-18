"""Add foreign key constraints from bot child tables to trading_bots with ON DELETE CASCADE.

Revision ID: 042
Revises: 041
"""
from alembic import op

revision = "042"
down_revision = "041"
branch_labels = None
depends_on = None

# (table, column, constraint_name)
CHILD_TABLES = [
    ("bot_files", "bot_id", "fk_bot_files_bot_id"),
    ("bot_executions", "bot_id", "fk_bot_executions_bot_id"),
    ("bot_positions", "bot_id", "fk_bot_positions_bot_id"),
    ("bot_wakeups", "bot_id", "fk_bot_wakeups_bot_id"),
    ("trade_logs", "bot_id", "fk_trade_logs_bot_id"),
]


def upgrade() -> None:
    # Clean up orphaned rows that reference deleted bots
    for table, column, _ in CHILD_TABLES:
        op.execute(
            f"DELETE FROM {table} WHERE {column} NOT IN (SELECT id FROM trading_bots)"
        )

    for table, column, constraint_name in CHILD_TABLES:
        op.create_foreign_key(
            constraint_name,
            table,
            "trading_bots",
            [column],
            ["id"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    for table, _, constraint_name in CHILD_TABLES:
        op.drop_constraint(constraint_name, table, type_="foreignkey")
