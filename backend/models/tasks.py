"""
Agent tasks — a unit of long-running work, one markdown file per task.

The file in the sandbox is the source of truth; this table is the synced,
queryable mirror that the app reads (the same arrangement as stock_analysis,
which mirrors stocks/{SYMBOL}/*.md). The agent writes `tasks/{slug}.md` with
YAML frontmatter and the sync hook in file_management parses it into a row.

Why files rather than rows the agent writes directly: the agent already reads
and writes markdown well, the task body stays diffable and human-editable, and
the directory doubles as the agent's work queue (`review` is the due date it
pulls from). The DB copy exists so the *app* can list and filter without
booting a sandbox.
"""
import uuid

from sqlalchemy import (Column, String, Text, Date, DateTime, ForeignKey,
                        UniqueConstraint, func)
from sqlalchemy.dialects.postgresql import UUID, JSONB

from core.database import Base

# Lifecycle. `dropped` is deliberately distinct from `done` — abandoning a
# thesis is a different signal from concluding one, and the agent should be
# able to tell them apart when it reviews its own track record.
TASK_STATUSES = ("open", "blocked", "done", "dropped")


class AgentTask(Base):
    __tablename__ = "agent_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, nullable=False, index=True)
    # Stable identity: the filename stem. Re-writing the same file updates the
    # row rather than creating a second one.
    slug = Column(String(200), nullable=False)
    title = Column(String(300), nullable=True)
    status = Column(String(20), nullable=False, default="open", index=True)
    body = Column(Text, nullable=True)
    symbols = Column(JSONB, nullable=True)
    opened_on = Column(Date, nullable=True)
    review_on = Column(Date, nullable=True, index=True)
    chat_id = Column(UUID(as_uuid=True), ForeignKey("chats.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "slug", name="uq_agent_tasks_user_slug"),
    )

    def __repr__(self):
        return f"<AgentTask(user='{self.user_id}', slug='{self.slug}', status='{self.status}')>"
