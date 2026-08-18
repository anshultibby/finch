"""
CRUD operations for transactions
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from typing import List, Optional, Dict, Any
from datetime import datetime
from models.brokerage import Transaction, TransactionSyncJob


def get_transactions(
    db: Session,
    user_id: str,
    symbol: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    transaction_types: Optional[List[str]] = None,
    limit: int = 1000
) -> List[Transaction]:
    """Get user's transactions with filters"""
    query = db.query(Transaction).filter(Transaction.user_id == user_id)
    
    if symbol:
        query = query.filter(Transaction.symbol == symbol.upper())
    
    if start_date:
        query = query.filter(Transaction.transaction_date >= start_date)
    
    if end_date:
        query = query.filter(Transaction.transaction_date <= end_date)
    
    if transaction_types:
        query = query.filter(Transaction.transaction_type.in_([t.upper() for t in transaction_types]))
    
    return query.order_by(desc(Transaction.transaction_date)).limit(limit).all()


def get_transaction_by_external_id(
    db: Session,
    user_id: str,
    external_id: str
) -> Optional[Transaction]:
    """Get transaction by external ID (SnapTrade ID)"""
    return db.query(Transaction).filter(
        and_(
            Transaction.user_id == user_id,
            Transaction.external_id == external_id
        )
    ).first()


def upsert_transaction(
    db: Session,
    user_id: str,
    account_id: str,
    symbol: str,
    transaction_type: str,
    transaction_date: datetime,
    data: Dict[str, Any],
    external_id: Optional[str] = None,
    auto_commit: bool = True,
) -> tuple[Transaction, bool]:
    """
    Create or update transaction.
    Returns (transaction, is_new).
    Set auto_commit=False for batch operations (caller must commit).
    """
    existing = None
    if external_id:
        existing = get_transaction_by_external_id(db, user_id, external_id)

    if existing:
        existing.symbol = symbol.upper()
        existing.transaction_type = transaction_type.upper()
        existing.transaction_date = transaction_date
        existing.account_id = account_id
        existing.data = data
        if auto_commit:
            db.commit()
            db.refresh(existing)
        return existing, False
    else:
        transaction = Transaction(
            user_id=user_id,
            account_id=account_id,
            symbol=symbol.upper(),
            transaction_type=transaction_type.upper(),
            transaction_date=transaction_date,
            external_id=external_id,
            data=data
        )
        db.add(transaction)
        if auto_commit:
            db.commit()
            db.refresh(transaction)
        return transaction, True


def create_sync_job(
    db: Session,
    user_id: str,
    status: str,
    data: Dict[str, Any]
) -> TransactionSyncJob:
    """Create a sync job record"""
    job = TransactionSyncJob(
        user_id=user_id,
        status=status,
        data=data
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def update_sync_job(
    db: Session,
    job_id: str,
    status: str,
    data: Dict[str, Any],
    completed_at: Optional[datetime] = None
) -> TransactionSyncJob:
    """Update sync job status"""
    job = db.query(TransactionSyncJob).filter(TransactionSyncJob.id == job_id).first()
    if job:
        job.status = status
        job.data = data
        if completed_at:
            job.completed_at = completed_at
        db.commit()
        db.refresh(job)
    return job


def get_latest_sync_job(db: Session, user_id: str) -> Optional[TransactionSyncJob]:
    """Get the most recent sync job for a user"""
    return db.query(TransactionSyncJob).filter(
        TransactionSyncJob.user_id == user_id
    ).order_by(desc(TransactionSyncJob.created_at)).first()

