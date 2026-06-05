"""
Brokerage ORM models: BrokerageAccount, Transaction, TransactionSyncJob, PortfolioSnapshot, PortfolioIntradayCache, TradeAnalytics, UserWatchlist, StockAnalysis
"""
from sqlalchemy import Column, String, DateTime, Text, Boolean, Integer, Date, UniqueConstraint, ForeignKey
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


class PortfolioHoldingsCache(Base):
    """
    Cached portfolio holdings response, keyed by user_id (one per user).
    Refreshed automatically when stale (> 5 minutes old).
    """
    __tablename__ = "portfolio_holdings_cache"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, nullable=False, unique=True, index=True)
    portfolio_data = Column(JSONB, nullable=False)
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


class WatchlistList(Base):
    """Named watchlist lists (e.g. 'AI Picks', 'My Watchlist', custom)"""
    __tablename__ = "watchlist_list"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    list_type = Column(String(20), server_default="custom", nullable=False)
    position = Column(Integer, server_default="0", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint('user_id', 'name', name='uq_watchlist_list_user_name'),
    )


class UserWatchlist(Base):
    """User's stock watchlist entries"""
    __tablename__ = "user_watchlist"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, nullable=False, index=True)
    symbol = Column(String(10), nullable=False)
    source = Column(String(20), server_default="manual", nullable=False)
    list_id = Column(UUID(as_uuid=True), ForeignKey("watchlist_list.id", ondelete="CASCADE"), nullable=True)
    added_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint('user_id', 'symbol', 'list_id', name='uq_watchlist_user_symbol_list'),
    )


class StockAnalysis(Base):
    """AI-generated stock analysis notes. Multiple notes per stock allowed."""
    __tablename__ = "stock_analysis"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, nullable=False, index=True)
    symbol = Column(String(10), nullable=False, index=True)
    filename = Column(String(200), nullable=True)
    title = Column(String(200), nullable=True)
    content = Column(Text, nullable=False)
    chat_id = Column(UUID(as_uuid=True), ForeignKey("chats.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint('user_id', 'symbol', 'filename', name='uq_stock_analysis_user_symbol_filename'),
    )


class Visualization(Base):
    """Agent-generated HTML visualizations (dashboards, trackers, charts)."""
    __tablename__ = "visualizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, nullable=False, index=True)
    chat_id = Column(String, ForeignKey("chats.chat_id", ondelete="SET NULL"), nullable=True)
    title = Column(String(200), nullable=True)
    description = Column(String(500), nullable=True)
    filename = Column(String(200), nullable=False)
    html_content = Column(Text, nullable=False)
    category = Column(String(100), nullable=True)
    tags = Column(JSONB, nullable=True, server_default="[]")
    is_public = Column(Boolean, server_default="false", nullable=False)
    share_token = Column(String(32), nullable=True, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint('user_id', 'filename', name='uq_viz_user_filename'),
    )


class PendingTrade(Base):
    """A trade staged by an automation, awaiting one-click email approval.

    Standalone (NOT bot-coupled): an automation reviews an order, stages it here,
    and emails the user an Approve/Reject link. Clicking Approve has the backend
    place the order via the Robinhood agentic MCP. The token in the link is the
    capability — anyone with it can approve, so links expire (expires_at).
    """
    __tablename__ = "pending_trades"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, nullable=False, index=True)
    token = Column(String(64), nullable=False, unique=True, index=True)
    broker = Column(String, nullable=False, server_default="robinhood")
    account_number = Column(String, nullable=False)
    # MCP order args: symbol, side, type, quantity|dollar_amount, limit_price, ...
    order_params = Column(JSONB, nullable=False)
    summary = Column(Text, nullable=True)  # human-readable preview (email + approve page)
    status = Column(String, nullable=False, server_default="pending", index=True)
    # status: pending | approved | rejected | expired | failed
    order_response = Column(JSONB, nullable=True)
    error = Column(Text, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    decided_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<PendingTrade(token='{self.token}', status='{self.status}', user='{self.user_id}')>"
