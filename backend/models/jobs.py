"""
Scheduled job ORM model.

An automation is a time (`run_at`, optionally repeating) and an instruction
(`message`). Either the user or the agent creates one; the waker claims due
rows with row-locking and runs the instruction as the user.

Everything else here is bookkeeping about past runs, plus two behaviour flags
set once at creation.
"""
from sqlalchemy import Column, String, Text, DateTime, Integer, Boolean
from sqlalchemy.sql import func
from core.database import Base


class ScheduledJob(Base):
    __tablename__ = "scheduled_jobs"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)

    # The automation itself.
    message = Column(Text, nullable=False)
    run_at = Column(DateTime(timezone=True), nullable=False, index=True)
    recurrence = Column(String, nullable=True)   # None | hourly | daily | weekly | weekdays | every_<N>m

    status = Column(String, nullable=False, default="pending", index=True)

    # Set on Finch-provisioned built-ins ("morning_brief", "heartbeat", …).
    # Doubles as the idempotency handle for schedule(): one row per key per user.
    # Built-ins are exempt from the per-user limits and are pausable, not
    # cancellable. Everything else about them is an ordinary automation.
    system_key = Column(String, nullable=True)

    # Behaviour that genuinely varies per job. Previously three module-level
    # sets keyed on system_key; now just columns.
    comped = Column(Boolean, nullable=False, default=False, server_default="false")
    activity_gated = Column(Boolean, nullable=False, default=False, server_default="false")

    # Run bookkeeping.
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    run_count = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
    last_run_credits = Column(Integer, nullable=False, default=0, server_default="0")
    credits_spent = Column(Integer, nullable=False, default=0, server_default="0")
