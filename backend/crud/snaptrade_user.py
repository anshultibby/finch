"""
CRUD operations for SnapTrade users
"""
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from datetime import datetime, timezone
from models.user import SnapTradeUser


def get_user_by_id(db: Session, user_id: str) -> Optional[SnapTradeUser]:
    """Get a SnapTrade user by user_id"""
    return db.query(SnapTradeUser).filter(
        SnapTradeUser.user_id == user_id
    ).first()


def delete_user(db: Session, user_id: str) -> bool:
    """Delete a SnapTrade user"""
    user = get_user_by_id(db, user_id)
    if user:
        db.delete(user)
        db.commit()
        return True
    return False


# --- Async versions (use with get_db_session() context manager) ---

async def get_user_by_id_async(db: AsyncSession, user_id: str) -> Optional[SnapTradeUser]:
    """Get a SnapTrade user by user_id (async)"""
    result = await db.execute(
        select(SnapTradeUser).filter(SnapTradeUser.user_id == user_id)
    )
    return result.scalars().first()


async def create_user_async(
    db: AsyncSession,
    user_id: str,
    snaptrade_user_id: str,
    snaptrade_user_secret: str,
) -> SnapTradeUser:
    """Create a new SnapTrade user record (async)"""
    db_user = SnapTradeUser(
        user_id=user_id,
        snaptrade_user_id=snaptrade_user_id,
        snaptrade_user_secret=snaptrade_user_secret,
        is_connected=False
    )
    db.add(db_user)
    await db.flush()
    await db.refresh(db_user)
    return db_user


async def update_connection_status_async(
    db: AsyncSession,
    user_id: str,
    is_connected: bool,
    account_ids: Optional[str] = None,
    brokerage_name: Optional[str] = None
) -> bool:
    """Update connection status and account info for a user (async)"""
    user = await get_user_by_id_async(db, user_id)
    if user:
        user.is_connected = is_connected
        if account_ids is not None:
            user.connected_account_ids = account_ids
        if brokerage_name is not None:
            user.brokerage_name = brokerage_name
        user.last_activity = datetime.now(timezone.utc)
        return True
    return False


async def delete_user_async(db: AsyncSession, user_id: str) -> bool:
    """Delete a SnapTrade user (async)"""
    user = await get_user_by_id_async(db, user_id)
    if user:
        await db.delete(user)
        return True
    return False

