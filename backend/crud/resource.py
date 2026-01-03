"""
CRUD operations for resources
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_
from models.db import Resource
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime


def create_resource(
    db: Session,
    chat_id: str,
    user_id: str,
    tool_name: str,
    resource_type: str,
    title: str,
    data: Dict[str, Any],
    resource_metadata: Optional[Dict[str, Any]] = None,
    resource_id: Optional[str] = None
) -> Resource:
    """
    Create or update a resource.
    
    If a resource with the same chat_id, title, and resource_type already exists,
    it will be updated instead of creating a duplicate.
    """
    # Check for existing resource with same chat_id + title + resource_type
    existing = db.query(Resource).filter(
        and_(
            Resource.chat_id == chat_id,
            Resource.title == title,
            Resource.resource_type == resource_type
        )
    ).first()
    
    if existing:
        # Update existing resource
        existing.tool_name = tool_name
        existing.data = data
        if resource_metadata is not None:
            existing.resource_metadata = resource_metadata
        db.commit()
        db.refresh(existing)
        return existing
    
    # Create new resource
    if resource_id is None:
        resource_id = str(uuid.uuid4())
    
    db_resource = Resource(
        id=resource_id,
        chat_id=chat_id,
        user_id=user_id,
        tool_name=tool_name,
        resource_type=resource_type,
        title=title,
        data=data,
        resource_metadata=resource_metadata
    )
    
    db.add(db_resource)
    db.commit()
    db.refresh(db_resource)
    
    return db_resource


def get_resource(db: Session, resource_id: str) -> Optional[Resource]:
    """
    Get a resource by ID
    """
    return db.query(Resource).filter(Resource.id == resource_id).first()


def get_chat_resources(
    db: Session, 
    chat_id: str, 
    limit: int = 100
) -> List[Resource]:
    """
    Get all resources for a chat
    """
    return (
        db.query(Resource)
        .filter(Resource.chat_id == chat_id)
        .order_by(Resource.created_at.desc())
        .limit(limit)
        .all()
    )


def get_user_resources(
    db: Session,
    user_id: str,
    limit: int = 100
) -> List[Resource]:
    """
    Get all resources for a user across all chats
    """
    return (
        db.query(Resource)
        .filter(Resource.user_id == user_id)
        .order_by(Resource.created_at.desc())
        .limit(limit)
        .all()
    )


def delete_resource(db: Session, resource_id: str) -> bool:
    """
    Delete a resource
    """
    resource = get_resource(db, resource_id)
    if resource:
        db.delete(resource)
        db.commit()
        return True
    return False


def delete_chat_resources(db: Session, chat_id: str) -> int:
    """
    Delete all resources for a chat
    Returns the number of resources deleted
    """
    count = db.query(Resource).filter(Resource.chat_id == chat_id).delete()
    db.commit()
    return count

