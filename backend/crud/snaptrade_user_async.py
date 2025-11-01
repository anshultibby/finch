"""
Async CRUD operations for SnapTrade users
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from datetime import datetime
from models.db import SnapTradeUser


async def create_user(
    db: AsyncSession,
    session_id: str,
    snaptrade_user_id: str,
    snaptrade_user_secret: str,
) -> SnapTradeUser:
    """
    Create a new SnapTrade user record
    
    Args:
        db: Async database session
        session_id: User session identifier
        snaptrade_user_id: SnapTrade user ID returned from registration
        snaptrade_user_secret: SnapTrade user secret returned from registration
    
    Returns:
        Created SnapTradeUser
    """
    db_user = SnapTradeUser(
        session_id=session_id,
        snaptrade_user_id=snaptrade_user_id,
        snaptrade_user_secret=snaptrade_user_secret,
        is_connected=False
    )
    
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


async def get_user_by_session(db: AsyncSession, session_id: str) -> Optional[SnapTradeUser]:
    """Get a SnapTrade user by session_id"""
    result = await db.execute(
        select(SnapTradeUser).where(SnapTradeUser.session_id == session_id)
    )
    return result.scalar_one_or_none()


async def get_user_by_snaptrade_id(db: AsyncSession, snaptrade_user_id: str) -> Optional[SnapTradeUser]:
    """Get a SnapTrade user by snaptrade_user_id"""
    result = await db.execute(
        select(SnapTradeUser).where(SnapTradeUser.snaptrade_user_id == snaptrade_user_id)
    )
    return result.scalar_one_or_none()


async def update_connection_status(
    db: AsyncSession,
    session_id: str,
    is_connected: bool,
    account_ids: Optional[str] = None,
    brokerage_name: Optional[str] = None
) -> bool:
    """Update connection status and account info for a user"""
    user = await get_user_by_session(db, session_id)
    if user:
        user.is_connected = is_connected
        if account_ids is not None:
            user.connected_account_ids = account_ids
        if brokerage_name is not None:
            user.brokerage_name = brokerage_name
        user.last_activity = datetime.utcnow()
        await db.commit()
        return True
    return False


async def update_activity(db: AsyncSession, session_id: str) -> bool:
    """Update last_activity timestamp for a user"""
    user = await get_user_by_session(db, session_id)
    if user:
        user.last_activity = datetime.utcnow()
        await db.commit()
        return True
    return False


async def delete_user(db: AsyncSession, session_id: str) -> bool:
    """Delete a SnapTrade user"""
    user = await get_user_by_session(db, session_id)
    if user:
        await db.delete(user)
        await db.commit()
        return True
    return False


async def disconnect_user(db: AsyncSession, session_id: str) -> bool:
    """Mark user as disconnected (soft delete)"""
    user = await get_user_by_session(db, session_id)
    if user:
        user.is_connected = False
        user.connected_account_ids = None
        user.last_activity = datetime.utcnow()
        await db.commit()
        return True
    return False

