"""
CRUD operations for brokerage accounts
"""
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.brokerage import BrokerageAccount
from datetime import datetime, timezone
from typing import Optional


def get_account_by_account_id(db: Session, user_id: str, account_id: str) -> Optional[BrokerageAccount]:
    """Get a brokerage account by SnapTrade account ID"""
    return db.query(BrokerageAccount).filter(
        BrokerageAccount.user_id == user_id,
        BrokerageAccount.account_id == account_id
    ).first()


def disconnect_account(db: Session, user_id: str, account_id: str) -> bool:
    """Mark an account as disconnected"""
    db_account = get_account_by_account_id(db, user_id, account_id)
    if db_account:
        db_account.is_active = False
        db_account.disconnected_at = datetime.now(timezone.utc)
        db.commit()
        return True
    return False


def delete_account(db: Session, user_id: str, account_id: str) -> bool:
    """Permanently delete an account record"""
    db_account = get_account_by_account_id(db, user_id, account_id)
    if db_account:
        db.delete(db_account)
        db.commit()
        return True
    return False


# --- Async versions (use with get_db_session() context manager) ---

async def get_account_by_account_id_async(db: AsyncSession, user_id: str, account_id: str) -> Optional[BrokerageAccount]:
    """Get a brokerage account by SnapTrade account ID (async)"""
    result = await db.execute(
        select(BrokerageAccount).filter(
            BrokerageAccount.user_id == user_id,
            BrokerageAccount.account_id == account_id
        )
    )
    return result.scalars().first()


async def disconnect_account_async(db: AsyncSession, user_id: str, account_id: str) -> bool:
    """Mark an account as disconnected (async)"""
    db_account = await get_account_by_account_id_async(db, user_id, account_id)
    if db_account:
        db_account.is_active = False
        db_account.disconnected_at = datetime.now(timezone.utc)
        return True
    return False


async def delete_all_accounts_async(db: AsyncSession, user_id: str) -> int:
    """Permanently delete all accounts for a user (async). Returns count deleted."""
    result = await db.execute(
        select(BrokerageAccount).filter(BrokerageAccount.user_id == user_id)
    )
    accounts = result.scalars().all()
    for account in accounts:
        await db.delete(account)
    return len(accounts)

