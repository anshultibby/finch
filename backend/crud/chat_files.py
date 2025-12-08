"""
CRUD operations for chat files (database-backed)
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_
from models.db import ChatFile
from typing import List, Optional, Dict
import uuid
import logging

logger = logging.getLogger(__name__)


def create_chat_file(
    db: Session,
    chat_id: str,
    user_id: str,
    filename: str,
    content: Optional[str] = None,
    file_type: str = "text",
    description: Optional[str] = None,
    metadata: Optional[Dict] = None,
    image_url: Optional[str] = None,
    size_bytes: Optional[int] = None
) -> ChatFile:
    """
    Create or update a chat file in database
    
    If file with same name exists in chat, it will be updated.
    For images: provide image_url instead of content
    For text files: provide content
    """
    # Check if file already exists
    existing = db.query(ChatFile).filter(
        and_(
            ChatFile.chat_id == chat_id,
            ChatFile.filename == filename
        )
    ).first()
    
    # Calculate size_bytes if not provided
    if size_bytes is None:
        if content:
            size_bytes = len(content.encode('utf-8'))
        else:
            size_bytes = 0
    
    if existing:
        # Update existing file
        existing.content = content
        existing.file_type = file_type
        existing.size_bytes = size_bytes
        existing.image_url = image_url
        if description:
            existing.description = description
        if metadata:
            existing.file_metadata = metadata
        db.commit()
        db.refresh(existing)
        logger.info(f"Updated chat file: {filename} in chat {chat_id}")
        return existing
    
    # Create new file
    file_obj = ChatFile(
        id=str(uuid.uuid4()),
        chat_id=chat_id,
        user_id=user_id,
        filename=filename,
        file_type=file_type,
        content=content,
        size_bytes=size_bytes,
        image_url=image_url,
        description=description,
        file_metadata=metadata or {}
    )
    
    db.add(file_obj)
    db.commit()
    db.refresh(file_obj)
    
    logger.info(f"Created chat file: {filename} in chat {chat_id}")
    return file_obj


def get_chat_file(
    db: Session,
    chat_id: str,
    filename: str
) -> Optional[ChatFile]:
    """Get a specific file from a chat"""
    return db.query(ChatFile).filter(
        and_(
            ChatFile.chat_id == chat_id,
            ChatFile.filename == filename
        )
    ).first()


def list_chat_files(
    db: Session,
    chat_id: str
) -> List[ChatFile]:
    """List all files in a chat"""
    return db.query(ChatFile).filter(
        ChatFile.chat_id == chat_id
    ).order_by(ChatFile.created_at.desc()).all()


def delete_chat_file(
    db: Session,
    chat_id: str,
    filename: str
) -> bool:
    """Delete a file from a chat"""
    file_obj = db.query(ChatFile).filter(
        and_(
            ChatFile.chat_id == chat_id,
            ChatFile.filename == filename
        )
    ).first()
    
    if file_obj:
        db.delete(file_obj)
        db.commit()
        logger.info(f"Deleted chat file: {filename} from chat {chat_id}")
        return True
    
    return False


def list_user_chat_files(
    db: Session,
    user_id: str
) -> List[ChatFile]:
    """List all files across all user's chats"""
    return db.query(ChatFile).filter(
        ChatFile.user_id == user_id
    ).order_by(ChatFile.created_at.desc()).all()

