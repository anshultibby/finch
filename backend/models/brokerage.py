"""
Brokerage ORM models: BrokerageAccount, Transaction, TransactionSyncJob, PortfolioSnapshot, PortfolioIntradayCache, TradeAnalytics
"""
from sqlalchemy import Column, String, DateTime, Text, Boolean, Integer, Date
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func
from core.database import Base
import uuid


class BrokerageAccount(Base):
    """
    Stores individual brokerage account connections
    """
    __tablename__ = "brokerage_accounts"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    account_id = Column(String, nullable=False, index=True)
    broker_id = Column(String, nullable=False)
    broker_name = Column(String, nullable=False)
    account_name = Column(String, nullable=True)
    account_number = Column(String, nullable=True)
    account_type = Column(String, nullable=True)
    balance = Column(Integer, nullable=True)
    account_metadata = Column(JSONB, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    connected_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    disconnected_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<BrokerageAccount(id='{self.id}', user='{self.user_id}', broker='{self.broker_name}', active={self.is_active})>"


class Transaction(Base):
    """
    Stores all user transactions - flexible JSON schema
    """
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(String, nullable=False, index=True)
    account_id = Column(String, nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    transaction_type = Column(String(20), nullable=False)
    transaction_date = Column(DateTime(timezone=True), nullable=False, index=True)
    external_id = Column(String, nullable=True)
    data = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<Transaction(id='{self.id}', symbol='{self.symbol}', type='{self.transaction_type}')>"


class TransactionSyncJob(Base):
    """
    Tracks sync operations - flexible JSON schema
    """
    __tablename__ = "transaction_sync_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(String, nullable=False, index=True)
    status = Column(String(20), nullable=False)
    data = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<TransactionSyncJob(id='{self.id}', user='{self.user_id}', status='{self.status}')>"


class PortfolioSnapshot(Base):
    """
    Daily portfolio snapshots - flexible JSON schema
    """
    __tablename__ = "portfolio_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(String, nullable=False, index=True)
    snapshot_date = Column(Date, nullable=False, index=True)
    data = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<PortfolioSnapshot(id='{self.id}', user='{self.user_id}', date='{self.snapshot_date}')>"


class PortfolioIntradayCache(Base):
    """
    Cached intraday portfolio equity series, keyed by user/account/days_back.
    Refreshed automatically when stale (> 1 hour old).
    """
    __tablename__ = "portfolio_intraday_cache"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, nullable=False, index=True)
    account_id = Column(String, nullable=True)
    days_back = Column(Integer, nullable=False)
    equity_series = Column(JSONB, nullable=False)
    computed_at = Column(DateTime(timezone=True), nullable=False)


class TradeAnalytics(Base):
    """
    Cached analysis results for closed positions - flexible JSON schema
    """
    __tablename__ = "trade_analytics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(String, nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    exit_date = Column(DateTime(timezone=True), nullable=False, index=True)
    data = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<TradeAnalytics(id='{self.id}', symbol='{self.symbol}')>"
