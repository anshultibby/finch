"""
Async CRUD operations for chats and chat messages
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from models.db import Chat, ChatMessage
from datetime import datetime


# Chat operations

async def create_chat(db: AsyncSession, chat_id: str, user_id: str, title: Optional[str] = None) -> Chat:
    """Create a new chat session"""
    db_chat = Chat(
        chat_id=chat_id,
        user_id=user_id,
        title=title
    )
    db.add(db_chat)
    await db.commit()
    await db.refresh(db_chat)
    return db_chat


async def get_chat(db: AsyncSession, chat_id: str) -> Optional[Chat]:
    """Get a chat by ID"""
    result = await db.execute(
        select(Chat).where(Chat.chat_id == chat_id)
    )
    return result.scalar_one_or_none()


async def get_user_chats(db: AsyncSession, user_id: str, limit: int = 50) -> List[Chat]:
    """Get all chats for a user, ordered by most recently updated"""
    result = await db.execute(
        select(Chat)
        .where(Chat.user_id == user_id)
        .order_by(Chat.updated_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def update_chat_title(db: AsyncSession, chat_id: str, title: str) -> Optional[Chat]:
    """Update a chat's title"""
    db_chat = await get_chat(db, chat_id)
    if db_chat:
        db_chat.title = title
        db_chat.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(db_chat)
    return db_chat


async def delete_chat(db: AsyncSession, chat_id: str) -> bool:
    """Delete a chat and all its messages"""
    # Delete messages first
    await db.execute(
        select(ChatMessage).where(ChatMessage.chat_id == chat_id)
    )
    
    # Delete chat
    result = await db.execute(
        select(Chat).where(Chat.chat_id == chat_id)
    )
    chat = result.scalar_one_or_none()
    if chat:
        await db.delete(chat)
        await db.commit()
        return True
    return False


# ChatMessage operations

async def create_message(
    db: AsyncSession,
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
        db: Async database session
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
    await db.commit()
    await db.refresh(db_message)
    
    # Update chat's updated_at timestamp
    db_chat = await get_chat(db, chat_id)
    if db_chat:
        db_chat.updated_at = datetime.utcnow()
        await db.commit()
    
    return db_message


async def update_message_resource(
    db: AsyncSession,
    message_id: int,
    resource_id: str
) -> Optional[ChatMessage]:
    """Link a resource to a message"""
    result = await db.execute(
        select(ChatMessage).where(ChatMessage.id == message_id)
    )
    db_message = result.scalar_one_or_none()
    if db_message:
        db_message.resource_id = resource_id
        await db.commit()
        await db.refresh(db_message)
    return db_message


async def get_chat_messages(db: AsyncSession, chat_id: str) -> List[ChatMessage]:
    """Get all messages for a chat, ordered by sequence"""
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.chat_id == chat_id)
        .order_by(ChatMessage.sequence.asc())
    )
    return list(result.scalars().all())


async def get_message_count(db: AsyncSession, chat_id: str) -> int:
    """Get the number of messages in a chat"""
    result = await db.execute(
        select(ChatMessage).where(ChatMessage.chat_id == chat_id)
    )
    return len(list(result.scalars().all()))


async def clear_chat_messages(db: AsyncSession, chat_id: str) -> int:
    """Clear all messages from a chat"""
    result = await db.execute(
        select(ChatMessage).where(ChatMessage.chat_id == chat_id)
    )
    messages = list(result.scalars().all())
    count = len(messages)
    for msg in messages:
        await db.delete(msg)
    await db.commit()
    return count

