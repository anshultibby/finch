"""
User-scoped memory store models: StoreFile and Dream.
"""
from sqlalchemy import Column, String, DateTime, Text, Integer
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func
from core.database import Base
import uuid


class StoreFile(Base):
    __tablename__ = "store_files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, nullable=False, index=True)
    filename = Column(String, nullable=False)
    content = Column(Text, nullable=True)
    file_type = Column(String, nullable=False, default="store")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<StoreFile(user='{self.user_id}', filename='{self.filename}')>"


class Dream(Base):
    __tablename__ = "dreams"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default="pending", index=True)
    trigger = Column(String, nullable=False)
    chat_ids = Column(JSONB, nullable=True)
    summary = Column(Text, nullable=True)
    self_score = Column(Integer, nullable=True)
    output_diff = Column(JSONB, nullable=True)
    follow_ups = Column(JSONB, nullable=True)
    token_usage = Column(JSONB, nullable=True)
    transcript = Column(JSONB, nullable=True)
    error = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<Dream(id='{self.id}', user='{self.user_id}', status='{self.status}')>"
