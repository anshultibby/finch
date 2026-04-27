"""
Chat-related ORM models: Chat, ChatMessage, ChatFile, Resource
"""
from sqlalchemy import Column, String, DateTime, Text, Boolean, Integer
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func
from core.database import Base
import uuid


class Chat(Base):
    """
    Stores chat session metadata
    """
    __tablename__ = "chats"

    chat_id = Column(String, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    title = Column(String, nullable=True)
    icon = Column(String(10), nullable=True)
    bot_id = Column(String, nullable=True, index=True)
    parent_chat_id = Column(String, nullable=True, index=True)
    is_processing = Column(Boolean, default=False, nullable=False, index=True)
    processing_started_at = Column(DateTime(timezone=True), nullable=True)
    notify_email = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<Chat(chat_id='{self.chat_id}', user_id='{self.user_id}', title='{self.title}', icon='{self.icon}', is_processing={self.is_processing})>"


class ChatMessageDB(Base):
    """
    Stores individual chat messages within a chat session (OpenAI format)

    Named ChatMessageDB to avoid collision with the Pydantic ChatMessage schema.
    Import as: from models.chat_models import ChatMessageDB as ChatMessage
    """
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(String, nullable=False, index=True)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    sequence = Column(Integer, nullable=False)
    tool_calls = Column(JSONB, nullable=True)
    tool_results = Column(JSONB, nullable=True)
    tool_call_id = Column(String, nullable=True, index=True)
    name = Column(String, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    resource_id = Column(String, nullable=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<ChatMessage(id={self.id}, chat_id='{self.chat_id}', role='{self.role}', seq={self.sequence})>"


class ChatFile(Base):
    """
    Stores files created during chat sessions
    """
    __tablename__ = "chat_files"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    chat_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    filename = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    content = Column(Text, nullable=True)
    size_bytes = Column(Integer, nullable=False)
    image_url = Column(String, nullable=True)
    description = Column(String, nullable=True)
    file_metadata = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<ChatFile(id='{self.id}', chat='{self.chat_id}', filename='{self.filename}')>"


class Resource(Base):
    """
    Stores function call results as resources that users can browse
    """
    __tablename__ = "resources"

    id = Column(String, primary_key=True, index=True)
    chat_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    tool_name = Column(String, nullable=False)
    resource_type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    data = Column(JSONB, nullable=False)
    resource_metadata = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    def __repr__(self):
        return f"<Resource(id='{self.id}', type='{self.resource_type}', tool='{self.tool_name}')>"


