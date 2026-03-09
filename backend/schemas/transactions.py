"""
Transaction and analytics Pydantic models

These models define the structure of the JSON data stored in JSONB columns.
The DB doesn't need to know about these fields - they're just for validation/typing.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from decimal import Decimal
from enum import Enum


class TransactionType(str, Enum):
    """Transaction types - STOCKS ONLY for MVP"""
    BUY = "BUY"
    SELL = "SELL"
    DIVIDEND = "DIVIDEND"
    FEE = "FEE"
    TRANSFER = "TRANSFER"
    SPLIT = "SPLIT"
    INTEREST = "INTEREST"


class AssetType(str, Enum):
    """Asset types - MVP supports stocks only"""
    STOCK = "STOCK"
    # Future: OPTION, CRYPTO, ETF, etc.


class TransactionData(BaseModel):
    """Structure of data stored in transactions.data JSONB field"""
    quantity: Decimal
    price: Optional[Decimal] = None
    fee: Decimal = Decimal(0)
    total_amount: Optional[Decimal] = None
    asset_type: AssetType = AssetType.STOCK
    settlement_date: Optional[datetime] = None
    cost_basis: Optional[Decimal] = None
    realized_pnl: Optional[Decimal] = None
    realized_pnl_percent: Optional[Decimal] = None
    description: Optional[str] = None
    currency: str = "USD"
    is_day_trade: bool = False
    holding_period_days: Optional[int] = None
    raw_data: Optional[Dict[str, Any]] = None  # Full SnapTrade response


class TransactionModel(BaseModel):
    """Complete transaction model (DB columns + data)"""
    id: str
    user_id: str
    account_id: str
    symbol: str
    transaction_type: TransactionType
    transaction_date: datetime
    external_id: Optional[str] = None
    data: TransactionData
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SnapshotData(BaseModel):
    """Structure of data stored in portfolio_snapshots.data JSONB field"""
    total_value: Decimal
    total_cost_basis: Optional[Decimal] = None
    unrealized_pnl: Optional[Decimal] = None
    unrealized_pnl_percent: Optional[Decimal] = None
    cash_balance: Decimal = Decimal(0)
    num_positions: int = 0
    holdings: Optional[List[Dict[str, Any]]] = None  # List of position details


class PortfolioSnapshotModel(BaseModel):
    """Complete portfolio snapshot model (DB columns + data)"""
    id: str
    user_id: str
    snapshot_date: date
    data: SnapshotData
    created_at: datetime

    class Config:
        from_attributes = True


class TradeAnalyticsData(BaseModel):
    """Structure of data stored in trade_analytics.data JSONB field"""
    entry_date: datetime
    entry_price: Decimal
    exit_price: Decimal
    quantity: Decimal
    holding_period_days: int
    total_cost: Decimal
    total_proceeds: Decimal
    realized_pnl: Decimal
    realized_pnl_percent: Decimal
    optimal_exit_price: Optional[Decimal] = None
    optimal_exit_date: Optional[datetime] = None
    potential_max_gain: Optional[Decimal] = None
    worst_drawdown: Optional[Decimal] = None
    trade_grade: Optional[str] = None  # A+, A, B, C, D, F
    trade_score: Optional[Decimal] = None  # 0-100
    is_winner: bool
    entry_context: Optional[Dict[str, Any]] = None
    exit_reason: Optional[str] = None
    ai_commentary: Optional[str] = None
    lessons_learned: Optional[List[str]] = None


class TradeAnalyticsModel(BaseModel):
    """Complete trade analytics model (DB columns + data)"""
    id: str
    user_id: str
    symbol: str
    exit_date: datetime
    data: TradeAnalyticsData
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PerformanceMetrics(BaseModel):
    """Overall portfolio performance metrics (computed, not stored)"""
    user_id: str
    period: str  # all_time, ytd, 1m, 3m, 6m, 1y
    
    # Returns
    total_return: Decimal
    total_return_percent: Decimal
    annualized_return_percent: Optional[Decimal] = None
    
    # Win/Loss stats
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: Decimal  # Percentage
    
    # Trade metrics
    avg_win_amount: Decimal
    avg_loss_amount: Decimal
    avg_win_percent: Decimal
    avg_loss_percent: Decimal
    profit_factor: Decimal  # Total wins / Total losses
    
    # Holding periods
    avg_holding_period_days: Decimal
    avg_holding_period_winners: Decimal
    avg_holding_period_losers: Decimal
    
    # Current portfolio
    current_value: Decimal
    total_invested: Decimal
    unrealized_pnl: Decimal
    realized_pnl: Decimal
    
    # Benchmarks
    sp500_return_percent: Optional[Decimal] = None
    alpha: Optional[Decimal] = None  # Performance vs S&P 500
    
    # Best/Worst
    best_trade: Optional[Dict[str, Any]] = None  # Simplified version
    worst_trade: Optional[Dict[str, Any]] = None
    
    # Risk metrics
    volatility: Optional[Decimal] = None
    sharpe_ratio: Optional[Decimal] = None
    max_drawdown: Optional[Decimal] = None
    
    calculated_at: datetime


class TradingPattern(BaseModel):
    """Behavioral pattern detected in user's trading"""
    pattern_type: str  # e.g., "early_exit", "panic_sell", "overtrading"
    confidence: float  # 0-1
    description: str
    examples: List[str]  # Trade IDs demonstrating pattern
    impact: str  # positive, negative, neutral
    recommendation: str


class ClosedPosition(BaseModel):
    """Represents a closed trading position (matched buy/sell pair)"""
    symbol: str
    entry_date: datetime
    exit_date: datetime
    entry_price: Decimal
    exit_price: Decimal
    quantity: Decimal
    total_cost: Decimal
    total_proceeds: Decimal
    realized_pnl: Decimal
    realized_pnl_percent: Decimal
    holding_period_days: int
    is_winner: bool


class TransactionSyncResult(BaseModel):
    """Result of a transaction sync operation"""
    success: bool
    message: str
    transactions_fetched: int = 0
    transactions_inserted: int = 0
    transactions_updated: int = 0
    accounts_synced: int = 0

