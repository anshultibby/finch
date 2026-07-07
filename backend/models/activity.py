"""Agent activity ledger — what the agent did on the user's behalf.

AgentEvent is append-only: automation runs, market alerts, trade proposals and
decisions, morning briefs. It backs the in-app activity feed and the
"while you were gone" recap. Notifications are interruptions; this is the
accounting record — including runs where the agent looked and did nothing.
"""
import uuid

from sqlalchemy import Column, String, Text, Integer, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB

from core.database import Base


class AgentEvent(Base):
    __tablename__ = "agent_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    # job_run | alert | trade_proposed | trade_decided | brief
    source = Column(String, nullable=True)  # automation | monitor | trade | brief
    title = Column(String, nullable=False)
    body = Column(Text, nullable=True)
    data = Column(JSONB, nullable=True)  # symbol, chat_id, job_id, pending_trade_id, ...
    value_cents = Column(Integer, nullable=True)  # dollar stake, when computable
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<AgentEvent(type='{self.event_type}', user='{self.user_id}', title='{self.title[:30]}')>"


class AgentActivitySeen(Base):
    """When the user last viewed the activity recap (one row per user)."""
    __tablename__ = "agent_activity_seen"

    user_id = Column(String, primary_key=True)
    seen_at = Column(DateTime(timezone=True), nullable=False)
