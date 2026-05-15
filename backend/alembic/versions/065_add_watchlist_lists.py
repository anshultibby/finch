"""add watchlist_list table and list_id to user_watchlist

Revision ID: 065
Revises: 064
Create Date: 2026-05-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "065"
down_revision = "064"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "watchlist_list",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.String(), nullable=False, index=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("list_type", sa.String(20), nullable=False, server_default="custom"),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "name", name="uq_watchlist_list_user_name"),
    )

    op.add_column("user_watchlist", sa.Column("list_id", UUID(as_uuid=True), nullable=True))

    # Create default lists for every existing user and assign items
    op.execute("""
        INSERT INTO watchlist_list (id, user_id, name, list_type, position)
        SELECT DISTINCT gen_random_uuid(), user_id, 'AI Picks', 'ai_picks', 0
        FROM user_watchlist
        ON CONFLICT DO NOTHING
    """)
    op.execute("""
        INSERT INTO watchlist_list (id, user_id, name, list_type, position)
        SELECT DISTINCT gen_random_uuid(), user_id, 'My Watchlist', 'my_watchlist', 1
        FROM user_watchlist
        ON CONFLICT DO NOTHING
    """)

    # Assign existing AI items to AI Picks list
    op.execute("""
        UPDATE user_watchlist w
        SET list_id = l.id
        FROM watchlist_list l
        WHERE l.user_id = w.user_id AND l.list_type = 'ai_picks' AND w.source = 'ai'
    """)

    # Assign existing manual items to My Watchlist list
    op.execute("""
        UPDATE user_watchlist w
        SET list_id = l.id
        FROM watchlist_list l
        WHERE l.user_id = w.user_id AND l.list_type = 'my_watchlist' AND w.list_id IS NULL
    """)

    op.drop_constraint("uq_watchlist_user_symbol", "user_watchlist", type_="unique")
    op.create_unique_constraint("uq_watchlist_user_symbol_list", "user_watchlist", ["user_id", "symbol", "list_id"])
    op.create_foreign_key("fk_watchlist_list_id", "user_watchlist", "watchlist_list", ["list_id"], ["id"], ondelete="CASCADE")


def downgrade():
    op.drop_constraint("fk_watchlist_list_id", "user_watchlist", type_="foreignkey")
    op.drop_constraint("uq_watchlist_user_symbol_list", "user_watchlist", type_="unique")
    op.create_unique_constraint("uq_watchlist_user_symbol", "user_watchlist", ["user_id", "symbol"])
    op.drop_column("user_watchlist", "list_id")
    op.drop_table("watchlist_list")
