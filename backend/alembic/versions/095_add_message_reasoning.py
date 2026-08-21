"""add chat_messages.reasoning — persist extended-thinking text per assistant turn

The agent's reasoning (extended thinking) is streamed live to the UI but was
never persisted, so it vanished on reload. This column stores the accumulated
reasoning text alongside the assistant message so history can render it as a
collapsed "Thought" disclosure. Display-only — it is NOT replayed to the model.

Revision ID: 095
Revises: 094
Create Date: 2026-08-19
"""
from alembic import op
import sqlalchemy as sa

revision = "095"
down_revision = "094"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("chat_messages", sa.Column("reasoning", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("chat_messages", "reasoning")
