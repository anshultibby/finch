"""
CRUD operations for brokerage accounts
"""
from sqlalchemy.orm import Session
from models.db import BrokerageAccount
from datetime import datetime
from typing import List, Optional
import uuid


def create_account(
    db: Session,
    user_id: str,
    account_id: str,
    broker_id: str,
    broker_name: str,
    account_name: Optional[str] = None,
    account_number: Optional[str] = None,
    account_type: Optional[str] = None,
    balance: Optional[float] = None,
    account_metadata: Optional[dict] = None
) -> BrokerageAccount:
    """Create a new brokerage account connection"""
    db_account = BrokerageAccount(
        id=str(uuid.uuid4()),
        user_id=user_id,
        account_id=account_id,
        broker_id=broker_id,
        broker_name=broker_name,
        account_name=account_name,
        account_number=account_number,
        account_type=account_type,
        balance=int(balance * 100) if balance is not None else None,  # Store in cents
        account_metadata=account_metadata,
        is_active=True,
        connected_at=datetime.utcnow(),
        last_synced_at=datetime.utcnow()
    )
    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    return db_account


def get_user_accounts(db: Session, user_id: str, active_only: bool = True) -> List[BrokerageAccount]:
    """Get all brokerage accounts for a user"""
    query = db.query(BrokerageAccount).filter(BrokerageAccount.user_id == user_id)
    if active_only:
        query = query.filter(BrokerageAccount.is_active == True)
    return query.order_by(BrokerageAccount.connected_at.desc()).all()


def get_account_by_id(db: Session, account_id: str) -> Optional[BrokerageAccount]:
    """Get a specific brokerage account by ID"""
    return db.query(BrokerageAccount).filter(BrokerageAccount.id == account_id).first()


def get_account_by_account_id(db: Session, user_id: str, account_id: str) -> Optional[BrokerageAccount]:
    """Get a brokerage account by SnapTrade account ID"""
    return db.query(BrokerageAccount).filter(
        BrokerageAccount.user_id == user_id,
        BrokerageAccount.account_id == account_id
    ).first()


def update_account_balance(db: Session, account_id: str, balance: float) -> Optional[BrokerageAccount]:
    """Update account balance"""
    db_account = get_account_by_account_id(db, account_id)
    if db_account:
        db_account.balance = int(balance * 100) if balance is not None else None
        db_account.last_synced_at = datetime.utcnow()
        db.commit()
        db.refresh(db_account)
    return db_account


def disconnect_account(db: Session, user_id: str, account_id: str) -> bool:
    """Mark an account as disconnected"""
    db_account = get_account_by_account_id(db, user_id, account_id)
    if db_account:
        db_account.is_active = False
        db_account.disconnected_at = datetime.utcnow()
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


def get_accounts_by_broker(db: Session, user_id: str, broker_id: str, active_only: bool = True) -> List[BrokerageAccount]:
    """Get all accounts for a specific broker"""
    query = db.query(BrokerageAccount).filter(
        BrokerageAccount.user_id == user_id,
        BrokerageAccount.broker_id == broker_id
    )
    if active_only:
        query = query.filter(BrokerageAccount.is_active == True)
    return query.all()

