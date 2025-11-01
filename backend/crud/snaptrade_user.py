"""
CRUD operations for SnapTrade users
"""
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from models.db import SnapTradeUser


def create_user(
    db: Session,
    user_id: str,
    snaptrade_user_id: str,
    snaptrade_user_secret: str,
) -> SnapTradeUser:
    """
    Create a new SnapTrade user record
    
    Args:
        db: Database session
        user_id: User identifier (Supabase UUID)
        snaptrade_user_id: SnapTrade user ID returned from registration
        snaptrade_user_secret: SnapTrade user secret returned from registration
    
    Returns:
        Created SnapTradeUser
    """
    db_user = SnapTradeUser(
        user_id=user_id,
        snaptrade_user_id=snaptrade_user_id,
        snaptrade_user_secret=snaptrade_user_secret,
        is_connected=False
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_user_by_id(db: Session, user_id: str) -> Optional[SnapTradeUser]:
    """Get a SnapTrade user by user_id"""
    return db.query(SnapTradeUser).filter(
        SnapTradeUser.user_id == user_id
    ).first()


def get_user_by_snaptrade_id(db: Session, snaptrade_user_id: str) -> Optional[SnapTradeUser]:
    """Get a SnapTrade user by snaptrade_user_id"""
    return db.query(SnapTradeUser).filter(
        SnapTradeUser.snaptrade_user_id == snaptrade_user_id
    ).first()


def update_connection_status(
    db: Session,
    user_id: str,
    is_connected: bool,
    account_ids: Optional[str] = None,
    brokerage_name: Optional[str] = None
) -> bool:
    """Update connection status and account info for a user"""
    user = get_user_by_id(db, user_id)
    if user:
        user.is_connected = is_connected
        if account_ids is not None:
            user.connected_account_ids = account_ids
        if brokerage_name is not None:
            user.brokerage_name = brokerage_name
        user.last_activity = datetime.utcnow()
        db.commit()
        return True
    return False


def update_activity(db: Session, user_id: str) -> bool:
    """Update last_activity timestamp for a user"""
    user = get_user_by_id(db, user_id)
    if user:
        user.last_activity = datetime.utcnow()
        db.commit()
        return True
    return False


def delete_user(db: Session, user_id: str) -> bool:
    """Delete a SnapTrade user"""
    user = get_user_by_id(db, user_id)
    if user:
        db.delete(user)
        db.commit()
        return True
    return False


def disconnect_user(db: Session, user_id: str) -> bool:
    """Mark user as disconnected (soft delete)"""
    user = get_user_by_id(db, user_id)
    if user:
        user.is_connected = False
        user.connected_account_ids = None
        user.last_activity = datetime.utcnow()
        db.commit()
        return True
    return False

