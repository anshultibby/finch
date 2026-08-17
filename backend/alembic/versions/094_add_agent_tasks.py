"""add agent_tasks — synced mirror of the agent's tasks/{slug}.md files

The agent tracks long-running work as one markdown file per task, with YAML
frontmatter (status, opened, symbols, review). The file is the source of truth;
this table is the queryable mirror the app lists from, the same way
stock_analysis mirrors stocks/{SYMBOL}/*.md.

Revision ID: 094
Revises: 093
Create Date: 2026-08-17
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "094"
down_revision = "093"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "agent_tasks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("slug", sa.String(200), nullable=False),
        sa.Column("title", sa.String(300), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("symbols", JSONB(), nullable=True),
        sa.Column("opened_on", sa.Date(), nullable=True),
        sa.Column("review_on", sa.Date(), nullable=True),
        sa.Column("chat_id", UUID(as_uuid=True),
                  sa.ForeignKey("chats.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "slug", name="uq_agent_tasks_user_slug"),
    )
    op.create_index("ix_agent_tasks_user_id", "agent_tasks", ["user_id"])
    op.create_index("ix_agent_tasks_status", "agent_tasks", ["status"])
    # The board's default query is "what's open and due" — one index covers it.
    op.create_index("ix_agent_tasks_review", "agent_tasks", ["user_id", "review_on"])


def downgrade():
    op.drop_index("ix_agent_tasks_review", table_name="agent_tasks")
    op.drop_index("ix_agent_tasks_status", table_name="agent_tasks")
    op.drop_index("ix_agent_tasks_user_id", table_name="agent_tasks")
    op.drop_table("agent_tasks")
