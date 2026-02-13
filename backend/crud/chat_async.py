"""
Async CRUD operations for chats and chat messages
"""
from typing import List, Optional, Set
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from models.db import Chat, ChatMessage
from datetime import datetime


# Chat operations

async def create_chat(db: AsyncSession, chat_id: str, user_id: str, title: Optional[str] = None, icon: Optional[str] = None) -> Chat:
    """Create a new chat session"""
    db_chat = Chat(
        chat_id=chat_id,
        user_id=user_id,
        title=title,
        icon=icon
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
    """Get all chats for a user, ordered by most recently created"""
    result = await db.execute(
        select(Chat)
        .where(Chat.user_id == user_id)
        .order_by(Chat.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_user_chats_with_preview(db: AsyncSession, user_id: str, limit: int = 50, max_length: int = 100) -> List[dict]:
    """
    Get all chats for a user with last message preview.
    Uses a single optimized query with subquery to avoid N+1 queries.
    """
    from sqlalchemy import func, literal_column
    from sqlalchemy.sql import text
    
    # Subquery to get the last user or assistant message for each chat
    # We'll do this in Python to avoid complex SQL - but efficiently
    result = await db.execute(
        select(Chat)
        .where(Chat.user_id == user_id)
        .order_by(Chat.created_at.desc())
        .limit(limit)
    )
    chats = result.scalars().all()
    
    # Batch fetch last messages for all chats in one query
    if chats:
        chat_ids = [chat.chat_id for chat in chats]
        
        # Get the latest message for each chat (user or assistant only)
        # Using a window function approach with SQLAlchemy
        from sqlalchemy import and_, or_
        
        messages_result = await db.execute(
            select(ChatMessage.chat_id, ChatMessage.content, ChatMessage.sequence)
            .where(
                and_(
                    ChatMessage.chat_id.in_(chat_ids),
                    or_(ChatMessage.role == 'user', ChatMessage.role == 'assistant')
                )
            )
            .order_by(ChatMessage.chat_id, ChatMessage.sequence.desc())
        )
        
        all_messages = messages_result.all()
        
        # Group by chat_id and get the first (most recent) message for each
        last_messages_by_chat = {}
        for msg in all_messages:
            if msg.chat_id not in last_messages_by_chat:
                last_messages_by_chat[msg.chat_id] = msg.content
    else:
        last_messages_by_chat = {}
    
    # Format results with previews
    chats_list = []
    for chat in chats:
        last_message = last_messages_by_chat.get(chat.chat_id)
        if last_message:
            # Truncate and clean up the message for preview
            last_message = last_message.strip()
            if len(last_message) > max_length:
                last_message = last_message[:max_length] + "..."
        
        chats_list.append({
            "chat_id": chat.chat_id,
            "title": chat.title,
            "icon": chat.icon,
            "created_at": chat.created_at.isoformat(),
            "updated_at": chat.updated_at.isoformat(),
            "last_message": last_message
        })
    
    return chats_list


async def get_last_message_preview(db: AsyncSession, chat_id: str, max_length: int = 100) -> Optional[str]:
    """Get a preview of the last user or assistant message in a chat"""
    from models.db import ChatMessage
    
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.chat_id == chat_id)
        .where(ChatMessage.role.in_(['user', 'assistant']))
        .order_by(ChatMessage.sequence.desc())
        .limit(1)
    )
    message = result.scalar_one_or_none()
    
    if message and message.content:
        # Truncate and clean up the message for preview
        content = message.content.strip()
        if len(content) > max_length:
            content = content[:max_length] + "..."
        return content
    
    return None


async def update_chat_title(db: AsyncSession, chat_id: str, title: str, icon: Optional[str] = None) -> Optional[Chat]:
    """Update a chat's title and optionally its icon"""
    db_chat = await get_chat(db, chat_id)
    if db_chat:
        db_chat.title = title
        if icon is not None:
            db_chat.icon = icon
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
    tool_results: Optional[dict] = None,
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
        tool_results: Optional tool execution results keyed by tool_call_id (for 'assistant' role)
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
        tool_results=tool_results,
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


async def delete_messages_by_ids(db: AsyncSession, message_ids: List[int]) -> int:
    """Delete messages by IDs and return count deleted."""
    if not message_ids:
        return 0
    result = await db.execute(
        select(ChatMessage).where(ChatMessage.id.in_(message_ids))
    )
    messages = list(result.scalars().all())
    for msg in messages:
        await db.delete(msg)
    await db.commit()
    return len(messages)


async def cleanup_incomplete_tool_sequences(db: AsyncSession, chat_id: str) -> int:
    """
    Remove incomplete tool call sequences that violate Anthropic requirements.
    
    Deletes assistant tool_calls that are not immediately followed by their tool
    results, along with any orphaned tool messages.
    """
    import json
    
    messages = await get_chat_messages(db, chat_id)
    if not messages:
        return 0
    
    delete_ids: Set[int] = set()
    valid_tool_call_ids: Set[str] = set()
    
    idx = 0
    while idx < len(messages):
        msg = messages[idx]
        
        if msg.role == "assistant":
            expected_ids = {tc.get("id") for tc in (msg.tool_calls or []) if tc.get("id")}
            # Also handle Claude-style tool_use blocks embedded in content
            content_ids: Set[str] = set()
            content = msg.content
            if isinstance(content, str) and content.strip().startswith("["):
                try:
                    parsed = json.loads(content)
                    if isinstance(parsed, list):
                        for block in parsed:
                            if isinstance(block, dict) and block.get("type") == "tool_use":
                                tool_use_id = block.get("id") or block.get("tool_use_id")
                                if tool_use_id:
                                    content_ids.add(tool_use_id)
                except json.JSONDecodeError:
                    content_ids = set()
            expected_ids |= content_ids
            
            if not expected_ids:
                idx += 1
                continue
            
            j = idx + 1
            seen_ids: Set[str] = set()
            contiguous_tool_ids: Set[str] = set()
            
            while j < len(messages) and messages[j].role == "tool":
                tool_call_id = messages[j].tool_call_id
                if tool_call_id:
                    seen_ids.add(tool_call_id)
                    contiguous_tool_ids.add(tool_call_id)
                j += 1
            
            if seen_ids == expected_ids:
                valid_tool_call_ids.update(expected_ids)
            else:
                delete_ids.add(msg.id)
                # Delete contiguous tool messages following this assistant
                for k in range(idx + 1, j):
                    delete_ids.add(messages[k].id)
                # Delete any tool messages matching expected ids anywhere
                for tool_msg in messages:
                    if tool_msg.role == "tool" and tool_msg.tool_call_id in expected_ids:
                        delete_ids.add(tool_msg.id)
            
            idx = j
            continue
        
        idx += 1
    
    # Delete orphan tool messages not tied to any valid tool call
    for msg in messages:
        if msg.role == "tool" and msg.tool_call_id and msg.tool_call_id not in valid_tool_call_ids:
            delete_ids.add(msg.id)
    
    return await delete_messages_by_ids(db, list(delete_ids))


async def get_message_count(db: AsyncSession, chat_id: str) -> int:
    """Get the number of messages in a chat"""
    result = await db.execute(
        select(ChatMessage).where(ChatMessage.chat_id == chat_id)
    )
    return len(list(result.scalars().all()))


async def get_next_sequence(db: AsyncSession, chat_id: str) -> int:
    """Get the next sequence number for a chat"""
    result = await db.execute(
        select(ChatMessage.sequence)
        .where(ChatMessage.chat_id == chat_id)
        .order_by(ChatMessage.sequence.desc())
        .limit(1)
    )
    max_seq = result.scalar_one_or_none()
    return 0 if max_seq is None else max_seq + 1


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


async def get_last_activity_timestamp(db: AsyncSession, chat_id: str) -> Optional[str]:
    """Get the timestamp of the last message in a chat (for activity tracking)"""
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.chat_id == chat_id)
        .order_by(ChatMessage.timestamp.desc())
        .limit(1)
    )
    last_message = result.scalar_one_or_none()
    
    if last_message and last_message.timestamp:
        return last_message.timestamp.isoformat()
    
    # Fall back to chat creation time if no messages
    chat = await get_chat(db, chat_id)
    if chat and chat.created_at:
        return chat.created_at.isoformat()
    
    return None


async def set_chat_processing(db: AsyncSession, chat_id: str, is_processing: bool) -> None:
    """
    Mark a chat as processing or not processing.
    Used for stream reconnection to track active streams.
    """
    from datetime import datetime
    
    chat = await get_chat(db, chat_id)
    if chat:
        chat.is_processing = is_processing
        chat.processing_started_at = datetime.now() if is_processing else None
        await db.commit()


async def is_chat_processing(db: AsyncSession, chat_id: str) -> bool:
    """
    Check if a chat is currently being processed.
    Also cleans up stale processing state (>5 minutes old).
    """
    from datetime import datetime, timedelta
    
    chat = await get_chat(db, chat_id)
    if not chat or not chat.is_processing:
        return False
    
    # Check if processing started recently (within last 5 minutes)
    if chat.processing_started_at:
        age = datetime.now() - chat.processing_started_at.replace(tzinfo=None)
        if age > timedelta(minutes=5):
            # Stale entry - clean it up
            chat.is_processing = False
            chat.processing_started_at = None
            await db.commit()
            return False
    
    return True

