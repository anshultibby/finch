"""
CRUD operations for resources
"""
from sqlalchemy.orm import Session
from models.chat_models import Resource
from typing import List, Optional


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


