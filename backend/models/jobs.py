"""
Scheduled job ORM model. A job is a message + planned execution time (+ optional
recurrence and context file paths). The waker claims due jobs with row-locking
and runs them by sending the message to the agent.
"""
from sqlalchemy import Column, String, Text, DateTime, Integer, JSON
from sqlalchemy.sql import func
from core.database import Base


class ScheduledJob(Base):
    __tablename__ = "scheduled_jobs"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    run_at = Column(DateTime(timezone=True), nullable=False, index=True)
    recurrence = Column(String, nullable=True)            # None | hourly | daily | weekly | weekdays
    priority = Column(Integer, nullable=False, default=5)  # 0 = highest
    status = Column(String, nullable=False, default="pending", index=True)
    chat_id = Column(String, nullable=True)
    context_paths = Column(JSON, nullable=True)           # list of sandbox file paths
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    run_count = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
    last_run_credits = Column(Integer, nullable=False, default=0, server_default="0")
    credits_spent = Column(Integer, nullable=False, default=0, server_default="0")
