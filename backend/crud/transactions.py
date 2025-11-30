"""
CRUD operations for transactions
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
from models.db import Transaction, PortfolioSnapshot, TradeAnalytics, TransactionSyncJob
from decimal import Decimal
import uuid


def create_transaction(
    db: Session,
    user_id: str,
    account_id: str,
    symbol: str,
    transaction_type: str,
    transaction_date: datetime,
    data: Dict[str, Any],
    external_id: Optional[str] = None
) -> Transaction:
    """Create a new transaction record"""
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
    db.commit()
    db.refresh(transaction)
    return transaction


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
    external_id: Optional[str] = None
) -> tuple[Transaction, bool]:
    """
    Create or update transaction
    Returns (transaction, is_new)
    """
    existing = None
    if external_id:
        existing = get_transaction_by_external_id(db, user_id, external_id)
    
    if existing:
        # Update existing
        existing.symbol = symbol.upper()
        existing.transaction_type = transaction_type.upper()
        existing.transaction_date = transaction_date
        existing.account_id = account_id
        existing.data = data
        db.commit()
        db.refresh(existing)
        return existing, False
    else:
        # Create new
        tx = create_transaction(
            db, user_id, account_id, symbol, transaction_type,
            transaction_date, data, external_id
        )
        return tx, True


def create_portfolio_snapshot(
    db: Session,
    user_id: str,
    snapshot_date: date,
    data: Dict[str, Any]
) -> PortfolioSnapshot:
    """Create or update daily portfolio snapshot"""
    snapshot = db.query(PortfolioSnapshot).filter(
        and_(
            PortfolioSnapshot.user_id == user_id,
            PortfolioSnapshot.snapshot_date == snapshot_date
        )
    ).first()
    
    if snapshot:
        # Update existing
        snapshot.data = data
    else:
        # Create new
        snapshot = PortfolioSnapshot(
            user_id=user_id,
            snapshot_date=snapshot_date,
            data=data
        )
        db.add(snapshot)
    
    db.commit()
    db.refresh(snapshot)
    return snapshot


def get_portfolio_snapshots(
    db: Session,
    user_id: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> List[PortfolioSnapshot]:
    """Get historical portfolio snapshots"""
    query = db.query(PortfolioSnapshot).filter(PortfolioSnapshot.user_id == user_id)
    
    if start_date:
        query = query.filter(PortfolioSnapshot.snapshot_date >= start_date)
    
    if end_date:
        query = query.filter(PortfolioSnapshot.snapshot_date <= end_date)
    
    return query.order_by(desc(PortfolioSnapshot.snapshot_date)).all()


def create_trade_analytics(
    db: Session,
    user_id: str,
    symbol: str,
    exit_date: datetime,
    data: Dict[str, Any]
) -> TradeAnalytics:
    """Create trade analytics record"""
    analytics = TradeAnalytics(
        user_id=user_id,
        symbol=symbol.upper(),
        exit_date=exit_date,
        data=data
    )
    db.add(analytics)
    db.commit()
    db.refresh(analytics)
    return analytics


def get_trade_analytics(
    db: Session,
    user_id: str,
    symbol: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> List[TradeAnalytics]:
    """Get trade analytics with filters"""
    query = db.query(TradeAnalytics).filter(TradeAnalytics.user_id == user_id)
    
    if symbol:
        query = query.filter(TradeAnalytics.symbol == symbol.upper())
    
    if start_date:
        query = query.filter(TradeAnalytics.exit_date >= start_date)
    
    if end_date:
        query = query.filter(TradeAnalytics.exit_date <= end_date)
    
    return query.order_by(desc(TradeAnalytics.exit_date)).all()


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

