"""
CRUD operations for chats and chat messages
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from models.db import Chat, ChatMessage
from datetime import datetime


# Chat operations

def create_chat(db: Session, chat_id: str, user_id: str, title: Optional[str] = None) -> Chat:
    """Create a new chat session"""
    db_chat = Chat(
        chat_id=chat_id,
        user_id=user_id,
        title=title
    )
    db.add(db_chat)
    db.commit()
    db.refresh(db_chat)
    return db_chat


def get_chat(db: Session, chat_id: str) -> Optional[Chat]:
    """Get a chat by ID"""
    return db.query(Chat).filter(Chat.chat_id == chat_id).first()


def get_user_chats(db: Session, user_id: str, limit: int = 50) -> List[Chat]:
    """Get all chats for a user, ordered by most recently updated"""
    return db.query(Chat).filter(
        Chat.user_id == user_id
    ).order_by(
        Chat.updated_at.desc()
    ).limit(limit).all()


def update_chat_title(db: Session, chat_id: str, title: str) -> Optional[Chat]:
    """Update a chat's title"""
    db_chat = get_chat(db, chat_id)
    if db_chat:
        db_chat.title = title
        db_chat.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_chat)
    return db_chat


def delete_chat(db: Session, chat_id: str) -> bool:
    """Delete a chat and all its messages"""
    # Delete messages first
    db.query(ChatMessage).filter(ChatMessage.chat_id == chat_id).delete()
    
    # Delete chat
    result = db.query(Chat).filter(Chat.chat_id == chat_id).delete()
    db.commit()
    return result > 0


# ChatMessage operations

def create_message(
    db: Session,
    chat_id: str,
    role: str,
    content: str,
    sequence: int,
    resource_id: Optional[str] = None,
    tool_calls: Optional[list] = None,
    tool_call_id: Optional[str] = None,
    name: Optional[str] = None,
    latency_ms: Optional[int] = None
) -> ChatMessage:
    """
    Create a new chat message (OpenAI format)
    
    Args:
        db: Database session
        chat_id: Chat identifier
        role: Message role ('user', 'assistant', or 'tool')
        content: Message content
        sequence: Message sequence number
        resource_id: Optional resource ID (for 'tool' role messages linking to resources)
        tool_calls: Optional tool calls data (for 'assistant' role messages)
        tool_call_id: Optional tool call ID (for 'tool' role messages)
        name: Optional tool name (for 'tool' role messages)
        latency_ms: Optional latency in milliseconds (for 'assistant' role messages)
    """
    db_message = ChatMessage(
        chat_id=chat_id,
        role=role,
        content=content,
        sequence=sequence,
        resource_id=resource_id,
        tool_calls=tool_calls,
        tool_call_id=tool_call_id,
        name=name,
        latency_ms=latency_ms
    )
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    
    # Update chat's updated_at timestamp
    db_chat = get_chat(db, chat_id)
    if db_chat:
        db_chat.updated_at = datetime.utcnow()
        db.commit()
    
    return db_message


def update_message_resource(
    db: Session,
    message_id: int,
    resource_id: str
) -> Optional[ChatMessage]:
    """Link a resource to a message"""
    db_message = db.query(ChatMessage).filter(ChatMessage.id == message_id).first()
    if db_message:
        db_message.resource_id = resource_id
        db.commit()
        db.refresh(db_message)
    return db_message


def get_chat_messages(db: Session, chat_id: str) -> List[ChatMessage]:
    """Get all messages for a chat, ordered by sequence"""
    return db.query(ChatMessage).filter(
        ChatMessage.chat_id == chat_id
    ).order_by(
        ChatMessage.sequence.asc()
    ).all()


def get_next_sequence(db: Session, chat_id: str) -> int:
    """Get the next sequence number for a chat"""
    max_seq = db.query(ChatMessage.sequence).filter(
        ChatMessage.chat_id == chat_id
    ).order_by(
        ChatMessage.sequence.desc()
    ).limit(1).scalar()
    return 0 if max_seq is None else max_seq + 1


def get_message_count(db: Session, chat_id: str) -> int:
    """Get the number of messages in a chat"""
    return db.query(ChatMessage).filter(ChatMessage.chat_id == chat_id).count()


def clear_chat_messages(db: Session, chat_id: str) -> int:
    """Clear all messages from a chat"""
    result = db.query(ChatMessage).filter(ChatMessage.chat_id == chat_id).delete()
    db.commit()
    return result

