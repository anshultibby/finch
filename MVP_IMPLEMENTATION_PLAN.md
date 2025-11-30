# Finch MVP: Trade Analyzer & Performance Coach

## 🎯 Vision Statement

**"Your AI investing coach that analyzes every trade you make, identifies patterns in your behavior, and helps you become a better investor through personalized insights and recommendations."**

Think: **Strava for investing** - track performance, learn from data, improve over time.

---

## 📋 MVP Scope: Phase 1 - Trade Analyzer

### What We're Building

A portfolio performance analysis platform that:
1. **Imports** your complete transaction history from connected brokerages
2. **Analyzes** your trading patterns, win/loss ratios, and behavioral tendencies
3. **Grades** individual trades and identifies what you're doing right/wrong
4. **Teaches** you to be a better investor through AI-powered insights
5. **Suggests** next moves based on your style + market opportunities

### Scope Limitations (MVP)

**INCLUDED:**
- ✅ Stock transactions (buys, sells)
- ✅ Dividends and fees
- ✅ Multiple brokerage accounts
- ✅ Historical performance analysis
- ✅ Pattern recognition

**EXCLUDED (Future Phases):**
- ❌ Options trading (calls, puts, spreads)
- ❌ Crypto/digital assets
- ❌ Forex trading
- ❌ Futures and commodities
- ❌ Complex derivatives

**Focus: Stock trading only** - This simplifies cost basis tracking, P&L calculations, and makes the MVP faster to build and easier to understand.

### What Makes This Different

- **Personal, not generic**: Analysis based on YOUR actual trades, not theoretical portfolios
- **Educational**: Every insight teaches you something about your investing behavior
- **Actionable**: Clear recommendations, not just data dumps
- **Conversational**: Chat with an AI coach, don't struggle with complex dashboards
- **Multi-source**: Combines your trades + insider activity + sentiment + fundamentals

---

## 🏗️ Technical Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                      FRONTEND (Next.js)                      │
├─────────────────────────────────────────────────────────────┤
│  - Performance Dashboard (new)                               │
│  - Trade Journal View (new)                                  │
│  - Chat Interface (existing, enhanced)                       │
│  - Portfolio View (existing)                                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     BACKEND (FastAPI)                        │
├─────────────────────────────────────────────────────────────┤
│  NEW ENDPOINTS:                                              │
│  - POST /api/transactions/sync                               │
│  - GET  /api/transactions/history                            │
│  - GET  /api/analytics/performance                           │
│  - GET  /api/analytics/trades/{trade_id}                     │
│  - GET  /api/analytics/patterns                              │
│                                                               │
│  NEW TOOLS (for LLM):                                        │
│  - get_transaction_history()                                 │
│  - analyze_portfolio_performance()                           │
│  - analyze_closed_positions()                                │
│  - analyze_trading_patterns()                                │
│  - grade_individual_trade()                                  │
│  - suggest_opportunities()                                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   DATA LAYER (PostgreSQL)                    │
├─────────────────────────────────────────────────────────────┤
│  NEW TABLES:                                                 │
│  - transactions (buys, sells, dividends)                     │
│  - transaction_sync_jobs (tracking sync status)              │
│  - portfolio_snapshots (historical portfolio values)         │
│  - trade_analytics (cached analysis results)                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    EXTERNAL DATA SOURCES                     │
├─────────────────────────────────────────────────────────────┤
│  - SnapTrade API: Transactions, Holdings, Accounts           │
│  - FMP API: Historical prices, fundamentals, benchmarks      │
│  - ApeWisdom: Reddit sentiment (existing)                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 🗄️ Database Schema Changes

### New Tables

#### 1. `transactions`
Stores all user transactions (buys, sells, dividends, fees, etc.)

```sql
CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR NOT NULL,
    account_id VARCHAR NOT NULL,
    
    -- Transaction details
    symbol VARCHAR(20) NOT NULL,
    transaction_type VARCHAR(20) NOT NULL,  -- BUY, SELL, DIVIDEND, FEE, TRANSFER, SPLIT (stocks only)
    quantity DECIMAL(20, 8) NOT NULL,
    price DECIMAL(20, 4),
    fee DECIMAL(20, 4) DEFAULT 0,
    total_amount DECIMAL(20, 4),
    
    -- Asset type filter (MVP: stocks only)
    asset_type VARCHAR(20) DEFAULT 'STOCK',  -- STOCK (options/crypto in future)
    
    -- Timing
    transaction_date TIMESTAMP NOT NULL,
    settlement_date TIMESTAMP,
    
    -- P&L tracking (calculated)
    cost_basis DECIMAL(20, 4),              -- For sales: original cost
    realized_pnl DECIMAL(20, 4),            -- For sales: profit/loss
    realized_pnl_percent DECIMAL(10, 4),
    
    -- Metadata
    description TEXT,
    currency VARCHAR(3) DEFAULT 'USD',
    external_id VARCHAR,                     -- SnapTrade transaction ID
    raw_data JSONB,                          -- Full SnapTrade response
    
    -- Analytics flags
    is_day_trade BOOLEAN DEFAULT FALSE,
    holding_period_days INTEGER,             -- For sales
    
    -- Tracking
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Indexes
    INDEX idx_user_transactions (user_id, transaction_date DESC),
    INDEX idx_symbol_transactions (symbol, transaction_date DESC),
    INDEX idx_user_symbol (user_id, symbol, transaction_date DESC),
    
    -- Constraints
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES snaptrade_users(user_id),
    CONSTRAINT unique_external_id UNIQUE (user_id, external_id)
);
```

#### 2. `transaction_sync_jobs`
Tracks sync operations to avoid duplicate imports

```sql
CREATE TABLE transaction_sync_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR NOT NULL,
    account_id VARCHAR,
    
    -- Job details
    status VARCHAR(20) NOT NULL,             -- pending, running, completed, failed
    start_date DATE,
    end_date DATE,
    
    -- Results
    transactions_fetched INTEGER DEFAULT 0,
    transactions_inserted INTEGER DEFAULT 0,
    transactions_updated INTEGER DEFAULT 0,
    error_message TEXT,
    
    -- Timing
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_user_sync_jobs (user_id, created_at DESC),
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES snaptrade_users(user_id)
);
```

#### 3. `portfolio_snapshots`
Daily snapshots of portfolio value for performance tracking

```sql
CREATE TABLE portfolio_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR NOT NULL,
    
    -- Portfolio metrics
    snapshot_date DATE NOT NULL,
    total_value DECIMAL(20, 4) NOT NULL,
    total_cost_basis DECIMAL(20, 4),
    unrealized_pnl DECIMAL(20, 4),
    unrealized_pnl_percent DECIMAL(10, 4),
    
    -- Cash positions
    cash_balance DECIMAL(20, 4) DEFAULT 0,
    
    -- Holdings summary
    num_positions INTEGER DEFAULT 0,
    holdings_data JSONB,                     -- Detailed position breakdown
    
    -- Tracking
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Indexes
    INDEX idx_user_snapshots (user_id, snapshot_date DESC),
    CONSTRAINT unique_user_date UNIQUE (user_id, snapshot_date),
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES snaptrade_users(user_id)
);
```

#### 4. `trade_analytics`
Cached analysis results for closed positions

```sql
CREATE TABLE trade_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    
    -- Trade details
    entry_date TIMESTAMP NOT NULL,
    exit_date TIMESTAMP NOT NULL,
    holding_period_days INTEGER NOT NULL,
    
    -- Financial metrics
    entry_price DECIMAL(20, 4) NOT NULL,
    exit_price DECIMAL(20, 4) NOT NULL,
    quantity DECIMAL(20, 8) NOT NULL,
    total_cost DECIMAL(20, 4) NOT NULL,
    total_proceeds DECIMAL(20, 4) NOT NULL,
    realized_pnl DECIMAL(20, 4) NOT NULL,
    realized_pnl_percent DECIMAL(10, 4) NOT NULL,
    
    -- Performance analysis
    optimal_exit_price DECIMAL(20, 4),       -- Highest price during holding
    optimal_exit_date TIMESTAMP,
    potential_max_gain DECIMAL(20, 4),       -- What you could have made
    worst_drawdown DECIMAL(10, 4),           -- Max % drop while holding
    
    -- Grading
    trade_grade VARCHAR(2),                   -- A+, A, B, C, D, F
    trade_score DECIMAL(5, 2),                -- 0-100
    is_winner BOOLEAN NOT NULL,
    
    -- Context at entry
    entry_context JSONB,                      -- Market conditions, sentiment, etc.
    exit_reason VARCHAR(50),                  -- stop_loss, take_profit, manual, etc.
    
    -- AI analysis
    ai_commentary TEXT,                       -- What you did right/wrong
    lessons_learned TEXT[],                   -- Key takeaways
    
    -- Tracking
    analyzed_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Indexes
    INDEX idx_user_analytics (user_id, exit_date DESC),
    INDEX idx_symbol_analytics (symbol, exit_date DESC),
    INDEX idx_trade_grade (trade_grade),
    
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES snaptrade_users(user_id)
);
```

---

## 🔧 Backend Implementation

### 1. New Models (`backend/models/transactions.py`)

```python
"""
Transaction and analytics models
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


class Transaction(BaseModel):
    id: str
    user_id: str
    account_id: str
    symbol: str
    transaction_type: TransactionType
    quantity: Decimal
    price: Optional[Decimal] = None
    fee: Decimal = Decimal(0)
    total_amount: Optional<Decimal> = None
    transaction_date: datetime
    settlement_date: Optional[datetime] = None
    cost_basis: Optional[Decimal] = None
    realized_pnl: Optional[Decimal] = None
    realized_pnl_percent: Optional[Decimal] = None
    description: Optional[str] = None
    currency: str = "USD"
    external_id: Optional[str] = None
    is_day_trade: bool = False
    holding_period_days: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class PortfolioSnapshot(BaseModel):
    id: str
    user_id: str
    snapshot_date: date
    total_value: Decimal
    total_cost_basis: Optional[Decimal] = None
    unrealized_pnl: Optional[Decimal] = None
    unrealized_pnl_percent: Optional[Decimal] = None
    cash_balance: Decimal = Decimal(0)
    num_positions: int = 0
    holdings_data: Optional[Dict[str, Any]] = None
    created_at: datetime


class TradeAnalytics(BaseModel):
    id: str
    user_id: str
    symbol: str
    entry_date: datetime
    exit_date: datetime
    holding_period_days: int
    entry_price: Decimal
    exit_price: Decimal
    quantity: Decimal
    total_cost: Decimal
    total_proceeds: Decimal
    realized_pnl: Decimal
    realized_pnl_percent: Decimal
    optimal_exit_price: Optional[Decimal] = None
    optimal_exit_date: Optional[datetime] = None
    potential_max_gain: Optional[Decimal] = None
    worst_drawdown: Optional[Decimal] = None
    trade_grade: Optional[str] = None
    trade_score: Optional[Decimal] = None
    is_winner: bool
    entry_context: Optional[Dict[str, Any]] = None
    exit_reason: Optional[str] = None
    ai_commentary: Optional[str] = None
    lessons_learned: Optional[List[str]] = None
    analyzed_at: datetime
    created_at: datetime
    updated_at: datetime


class PerformanceMetrics(BaseModel):
    """Overall portfolio performance metrics"""
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
    best_trade: Optional[TradeAnalytics] = None
    worst_trade: Optional[TradeAnalytics] = None
    
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
```

### 2. CRUD Operations (`backend/crud/transactions.py`)

```python
"""
CRUD operations for transactions
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
from models.db import Transaction, PortfolioSnapshot, TradeAnalytics
from decimal import Decimal


def create_transaction(
    db: Session,
    user_id: str,
    account_id: str,
    symbol: str,
    transaction_type: str,
    quantity: Decimal,
    price: Optional[Decimal],
    transaction_date: datetime,
    **kwargs
) -> Transaction:
    """Create a new transaction record"""
    transaction = Transaction(
        user_id=user_id,
        account_id=account_id,
        symbol=symbol,
        transaction_type=transaction_type,
        quantity=quantity,
        price=price,
        transaction_date=transaction_date,
        **kwargs
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
        query = query.filter(Transaction.symbol == symbol)
    
    if start_date:
        query = query.filter(Transaction.transaction_date >= start_date)
    
    if end_date:
        query = query.filter(Transaction.transaction_date <= end_date)
    
    if transaction_types:
        query = query.filter(Transaction.transaction_type.in_(transaction_types))
    
    return query.order_by(desc(Transaction.transaction_date)).limit(limit).all()


def get_closed_positions(db: Session, user_id: str) -> List[Dict[str, Any]]:
    """
    Calculate closed positions (matched buy/sell pairs)
    Returns list of closed trades with P&L
    """
    # This is complex - needs to match FIFO lots
    # Implementation will use FIFO accounting
    pass


def create_portfolio_snapshot(
    db: Session,
    user_id: str,
    snapshot_date: date,
    total_value: Decimal,
    **kwargs
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
        snapshot.total_value = total_value
        for key, value in kwargs.items():
            setattr(snapshot, key, value)
    else:
        # Create new
        snapshot = PortfolioSnapshot(
            user_id=user_id,
            snapshot_date=snapshot_date,
            total_value=total_value,
            **kwargs
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
```

### 3. Transaction Sync Service (`backend/services/transaction_sync.py`)

```python
"""
Service for syncing transactions from SnapTrade
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import asyncio
from database import SessionLocal
from crud import transactions as tx_crud
from modules.tools.clients.snaptrade import snaptrade_tools


class TransactionSyncService:
    """Handles syncing transactions from SnapTrade to local database"""
    
    async def sync_user_transactions(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        force_resync: bool = False
    ) -> Dict[str, Any]:
        """
        Sync all transactions for a user from SnapTrade
        
        Args:
            user_id: User ID
            start_date: Optional start date (defaults to account inception)
            end_date: Optional end date (defaults to today)
            force_resync: If True, re-fetch even if already synced
            
        Returns:
            Dictionary with sync results
        """
        try:
            # Get user's accounts
            session = snaptrade_tools._get_session(user_id)
            if not session or not session.is_connected:
                return {
                    "success": False,
                    "message": "No active brokerage connection"
                }
            
            # Get accounts
            accounts = await snaptrade_tools._get_accounts(
                user_id,
                session.snaptrade_user_secret
            )
            
            total_fetched = 0
            total_inserted = 0
            total_updated = 0
            
            # Sync each account
            for account in accounts:
                result = await self._sync_account_transactions(
                    user_id=user_id,
                    user_secret=session.snaptrade_user_secret,
                    account_id=account.id,
                    start_date=start_date,
                    end_date=end_date
                )
                total_fetched += result["fetched"]
                total_inserted += result["inserted"]
                total_updated += result["updated"]
            
            # Calculate portfolio metrics after sync
            await self._calculate_portfolio_metrics(user_id)
            
            return {
                "success": True,
                "transactions_fetched": total_fetched,
                "transactions_inserted": total_inserted,
                "transactions_updated": total_updated,
                "accounts_synced": len(accounts)
            }
            
        except Exception as e:
            print(f"Error syncing transactions: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "message": f"Sync failed: {str(e)}"
            }
    
    async def _sync_account_transactions(
        self,
        user_id: str,
        user_secret: str,
        account_id: str,
        start_date: Optional[datetime],
        end_date: Optional[datetime]
    ) -> Dict[str, int]:
        """Sync transactions for a specific account"""
        
        # Call SnapTrade activities API
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: snaptrade_tools.client.transactions_and_reporting.get_activities(
                user_id=user_id,
                user_secret=user_secret,
                account_id=account_id,
                start_date=start_date.strftime("%Y-%m-%d") if start_date else None,
                end_date=end_date.strftime("%Y-%m-%d") if end_date else None
            )
        )
        
        activities = response.body if hasattr(response, 'body') else response
        
        fetched = len(activities)
        inserted = 0
        updated = 0
        
        db = SessionLocal()
        try:
            for activity in activities:
                # Parse activity into transaction (returns None for non-stock transactions)
                tx_data = self._parse_snaptrade_activity(activity, user_id, account_id)
                
                # Skip if not a stock transaction (MVP limitation)
                if tx_data is None:
                    continue
                
                # Check if exists
                existing = db.query(Transaction).filter(
                    and_(
                        Transaction.user_id == user_id,
                        Transaction.external_id == tx_data["external_id"]
                    )
                ).first()
                
                if existing:
                    # Update
                    for key, value in tx_data.items():
                        setattr(existing, key, value)
                    updated += 1
                else:
                    # Insert
                    tx_crud.create_transaction(db, **tx_data)
                    inserted += 1
            
            db.commit()
        finally:
            db.close()
        
        return {
            "fetched": fetched,
            "inserted": inserted,
            "updated": updated
        }
    
    def _parse_snaptrade_activity(
        self,
        activity: Dict[str, Any],
        user_id: str,
        account_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Parse SnapTrade activity into transaction format
        
        Returns None if activity should be skipped (e.g., options trades in MVP)
        """
        
        # MVP: Skip non-stock transactions
        security_type = activity.get("type", "").upper()
        if security_type in ["OPTION", "CRYPTO", "FUTURE", "FOREX"]:
            print(f"⚠️ Skipping non-stock transaction: {security_type}", flush=True)
            return None
        
        # Map SnapTrade activity types to our types
        type_mapping = {
            "BUY": "BUY",
            "SELL": "SELL",
            "DIVIDEND": "DIVIDEND",
            "FEE": "FEE",
            "DEPOSIT": "TRANSFER",
            "WITHDRAWAL": "TRANSFER",
            "SPLIT": "SPLIT",
            "INTEREST": "INTEREST"
        }
        
        return {
            "user_id": user_id,
            "account_id": account_id,
            "symbol": activity.get("symbol", ""),
            "transaction_type": type_mapping.get(
                activity.get("type", "").upper(),
                "TRANSFER"
            ),
            "quantity": Decimal(str(activity.get("units", 0))),
            "price": Decimal(str(activity.get("price", 0))) if activity.get("price") else None,
            "fee": Decimal(str(activity.get("fee", 0))),
            "total_amount": Decimal(str(activity.get("amount", 0))),
            "transaction_date": datetime.fromisoformat(
                activity["trade_date"].replace("Z", "+00:00")
            ),
            "settlement_date": datetime.fromisoformat(
                activity["settlement_date"].replace("Z", "+00:00")
            ) if activity.get("settlement_date") else None,
            "description": activity.get("description"),
            "currency": activity.get("currency", "USD"),
            "external_id": activity.get("id", ""),
            "raw_data": activity
        }
    
    async def _calculate_portfolio_metrics(self, user_id: str):
        """Calculate and cache portfolio metrics after sync"""
        # This will calculate P&L, win rates, etc.
        # Implementation in analytics service
        pass


# Global instance
transaction_sync_service = TransactionSyncService()
```

### 4. Analytics Service (`backend/services/analytics.py`)

```python
"""
Portfolio analytics and performance calculations
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, date
from decimal import Decimal
from database import SessionLocal
from crud import transactions as tx_crud
from sqlalchemy import func, and_
import pandas as pd


class AnalyticsService:
    """Calculate portfolio performance metrics"""
    
    def calculate_performance_metrics(
        self,
        user_id: str,
        period: str = "all_time"
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive performance metrics
        
        Args:
            user_id: User ID
            period: Time period (all_time, ytd, 1m, 3m, 6m, 1y)
            
        Returns:
            PerformanceMetrics dictionary
        """
        db = SessionLocal()
        try:
            # Get date range for period
            start_date = self._get_period_start_date(period)
            
            # Get all transactions in period
            transactions = tx_crud.get_transactions(
                db, user_id, start_date=start_date
            )
            
            # Calculate closed positions
            closed_positions = self._calculate_closed_positions(transactions)
            
            # Calculate metrics
            metrics = {
                "user_id": user_id,
                "period": period,
                "calculated_at": datetime.now()
            }
            
            # Win/Loss stats
            winners = [p for p in closed_positions if p["realized_pnl"] > 0]
            losers = [p for p in closed_positions if p["realized_pnl"] < 0]
            
            metrics["total_trades"] = len(closed_positions)
            metrics["winning_trades"] = len(winners)
            metrics["losing_trades"] = len(losers)
            metrics["win_rate"] = (
                Decimal(len(winners)) / Decimal(len(closed_positions)) * 100
                if closed_positions else Decimal(0)
            )
            
            # P&L stats
            total_wins = sum(p["realized_pnl"] for p in winners)
            total_losses = abs(sum(p["realized_pnl"] for p in losers))
            
            metrics["avg_win_amount"] = (
                Decimal(total_wins) / Decimal(len(winners))
                if winners else Decimal(0)
            )
            metrics["avg_loss_amount"] = (
                Decimal(total_losses) / Decimal(len(losers))
                if losers else Decimal(0)
            )
            
            metrics["profit_factor"] = (
                Decimal(total_wins) / Decimal(total_losses)
                if total_losses > 0 else Decimal(0)
            )
            
            metrics["total_return"] = Decimal(total_wins) - Decimal(total_losses)
            
            # Holding periods
            if closed_positions:
                metrics["avg_holding_period_days"] = Decimal(
                    sum(p["holding_period_days"] for p in closed_positions) / len(closed_positions)
                )
                metrics["avg_holding_period_winners"] = Decimal(
                    sum(p["holding_period_days"] for p in winners) / len(winners)
                ) if winners else Decimal(0)
                metrics["avg_holding_period_losers"] = Decimal(
                    sum(p["holding_period_days"] for p in losers) / len(losers)
                ) if losers else Decimal(0)
            
            # Best/Worst trades
            if closed_positions:
                metrics["best_trade"] = max(closed_positions, key=lambda x: x["realized_pnl"])
                metrics["worst_trade"] = min(closed_positions, key=lambda x: x["realized_pnl"])
            
            return metrics
            
        finally:
            db.close()
    
    def _calculate_closed_positions(
        self,
        transactions: List[Any]
    ) -> List[Dict[str, Any]]:
        """
        Match buy/sell transactions using FIFO accounting
        Returns list of closed positions with P&L
        """
        # Group by symbol
        by_symbol = {}
        for tx in transactions:
            if tx.symbol not in by_symbol:
                by_symbol[tx.symbol] = []
            by_symbol[tx.symbol].append(tx)
        
        closed_positions = []
        
        for symbol, txs in by_symbol.items():
            # Sort by date
            txs.sort(key=lambda x: x.transaction_date)
            
            # FIFO matching
            buy_queue = []  # [(quantity, price, date, tx_id)]
            
            for tx in txs:
                if tx.transaction_type == "BUY":
                    buy_queue.append({
                        "quantity": tx.quantity,
                        "price": tx.price,
                        "date": tx.transaction_date,
                        "tx_id": tx.id
                    })
                
                elif tx.transaction_type == "SELL":
                    remaining_to_sell = tx.quantity
                    sell_price = tx.price
                    sell_date = tx.transaction_date
                    
                    while remaining_to_sell > 0 and buy_queue:
                        buy = buy_queue[0]
                        
                        # Match quantity
                        matched_qty = min(remaining_to_sell, buy["quantity"])
                        
                        # Calculate P&L
                        cost = matched_qty * buy["price"]
                        proceeds = matched_qty * sell_price
                        pnl = proceeds - cost
                        pnl_percent = (pnl / cost) * 100
                        
                        # Holding period
                        holding_days = (sell_date - buy["date"]).days
                        
                        closed_positions.append({
                            "symbol": symbol,
                            "entry_date": buy["date"],
                            "exit_date": sell_date,
                            "entry_price": buy["price"],
                            "exit_price": sell_price,
                            "quantity": matched_qty,
                            "total_cost": cost,
                            "total_proceeds": proceeds,
                            "realized_pnl": pnl,
                            "realized_pnl_percent": pnl_percent,
                            "holding_period_days": holding_days,
                            "is_winner": pnl > 0
                        })
                        
                        # Update queues
                        remaining_to_sell -= matched_qty
                        buy["quantity"] -= matched_qty
                        
                        if buy["quantity"] <= 0:
                            buy_queue.pop(0)
        
        return closed_positions
    
    def analyze_trading_patterns(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Detect behavioral patterns in trading
        Returns list of patterns with recommendations
        """
        db = SessionLocal()
        try:
            metrics = self.calculate_performance_metrics(user_id)
            transactions = tx_crud.get_transactions(db, user_id)
            
            patterns = []
            
            # Pattern: Early exit on winners
            if metrics["avg_holding_period_winners"] < metrics["avg_holding_period_losers"]:
                patterns.append({
                    "pattern_type": "early_exit_winners",
                    "confidence": 0.85,
                    "description": "You tend to sell winning positions too early",
                    "impact": "negative",
                    "recommendation": "Consider holding winners longer to maximize gains. Your average winning hold is {:.0f} days vs {:.0f} days for losers.".format(
                        metrics["avg_holding_period_winners"],
                        metrics["avg_holding_period_losers"]
                    )
                })
            
            # Pattern: Overtrading
            recent_30_days = [
                tx for tx in transactions
                if (datetime.now() - tx.transaction_date).days <= 30
            ]
            if len(recent_30_days) > 50:
                patterns.append({
                    "pattern_type": "overtrading",
                    "confidence": 0.90,
                    "description": f"High trading frequency: {len(recent_30_days)} trades in last 30 days",
                    "impact": "negative",
                    "recommendation": "Excessive trading can hurt returns due to fees and taxes. Consider a more patient approach."
                })
            
            # More patterns...
            
            return patterns
            
        finally:
            db.close()
    
    def _get_period_start_date(self, period: str) -> Optional[datetime]:
        """Get start date for a time period"""
        now = datetime.now()
        
        if period == "all_time":
            return None
        elif period == "ytd":
            return datetime(now.year, 1, 1)
        elif period == "1m":
            return now - timedelta(days=30)
        elif period == "3m":
            return now - timedelta(days=90)
        elif period == "6m":
            return now - timedelta(days=180)
        elif period == "1y":
            return now - timedelta(days=365)
        
        return None


# Global instance
analytics_service = AnalyticsService()
```

### 5. New Tools for LLM (`backend/modules/tools/definitions.py`)

Add these tools:

```python
@tool(
    description="""Fetch the user's complete transaction history including buys, sells, dividends, and fees. 
    This is essential for analyzing trading performance and identifying patterns.
    
    Use this when user asks about:
    - Past trades or transaction history
    - Performance analysis
    - What stocks they've traded
    - Trading patterns or behavior
    
    Parameters:
    - symbol: Optional ticker to filter (e.g., 'AAPL')
    - start_date: Optional start date (YYYY-MM-DD)
    - end_date: Optional end date (YYYY-MM-DD)
    - limit: Max transactions to return (default 100)
    """,
    category="portfolio"
)
async def get_transaction_history(
    *,
    context: AgentContext,
    symbol: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100
):
    """Get user's transaction history"""
    # Call transaction sync service first
    # Then return formatted transactions
    pass


@tool(
    description="""Analyze the user's overall portfolio performance including win rate, P&L, best/worst trades, 
    and behavioral patterns. This provides a comprehensive performance report.
    
    Use this when user asks:
    - "How am I doing?"
    - "Analyze my performance"
    - "What's my win rate?"
    - "Show me my best and worst trades"
    
    Parameters:
    - period: Time period to analyze (all_time, ytd, 1m, 3m, 6m, 1y)
    """,
    category="analytics"
)
async def analyze_portfolio_performance(
    *,
    context: AgentContext,
    period: str = "all_time"
):
    """Analyze overall portfolio performance"""
    from services.analytics import analytics_service
    
    yield SSEEvent(
        event="tool_status",
        data={
            "status": "analyzing",
            "message": f"Analyzing your trading performance ({period})..."
        }
    )
    
    metrics = analytics_service.calculate_performance_metrics(
        context.user_id,
        period=period
    )
    
    yield {
        "success": True,
        "data": metrics,
        "message": f"Performance analysis complete for {period}"
    }


@tool(
    description="""Analyze a specific closed trade in detail, including what you could have done better,
    optimal exit points, and lessons learned.
    
    Use this when user asks:
    - "Why did I lose money on TSLA?"
    - "Grade my AAPL trade"
    - "What did I do wrong on that trade?"
    
    Parameters:
    - symbol: Stock symbol
    - entry_date: Optional entry date to identify specific trade
    """,
    category="analytics"
)
async def analyze_specific_trade(
    *,
    context: AgentContext,
    symbol: str,
    entry_date: Optional[str] = None
):
    """Analyze a specific closed position"""
    # Grade the trade, find optimal exit, provide commentary
    pass


@tool(
    description="""Identify behavioral patterns in the user's trading such as:
    - Early exit on winners
    - Holding losers too long
    - Overtrading
    - Panic selling
    - Sector bias
    
    Use this when user asks:
    - "What patterns do you see in my trading?"
    - "What am I doing wrong?"
    - "How can I improve?"
    """,
    category="analytics"
)
async def identify_trading_patterns(
    *,
    context: AgentContext
):
    """Identify behavioral patterns"""
    from services.analytics import analytics_service
    
    patterns = analytics_service.analyze_trading_patterns(context.user_id)
    
    yield {
        "success": True,
        "data": {
            "patterns": patterns
        },
        "message": f"Found {len(patterns)} trading patterns"
    }
```

### 6. API Routes (`backend/routes/analytics.py`)

```python
"""
Analytics API routes
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from datetime import datetime
from services.analytics import analytics_service
from services.transaction_sync import transaction_sync_service
from modules.agent.context import get_user_id


router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.post("/transactions/sync")
async def sync_transactions(user_id: str = Depends(get_user_id)):
    """Sync transactions from SnapTrade"""
    result = await transaction_sync_service.sync_user_transactions(user_id)
    return result


@router.get("/performance")
async def get_performance(
    period: str = "all_time",
    user_id: str = Depends(get_user_id)
):
    """Get performance metrics"""
    metrics = analytics_service.calculate_performance_metrics(user_id, period)
    return metrics


@router.get("/patterns")
async def get_trading_patterns(user_id: str = Depends(get_user_id)):
    """Get behavioral patterns"""
    patterns = analytics_service.analyze_trading_patterns(user_id)
    return {"patterns": patterns}
```

---

## 🎨 Frontend Implementation

### 1. Performance Dashboard Component

Create `frontend/components/PerformanceDashboard.tsx`:

```typescript
'use client';

import React, { useEffect, useState } from 'react';
import { analyticsApi, PerformanceMetrics } from '@/lib/api';

export default function PerformanceDashboard({ userId }: { userId: string }) {
  const [metrics, setMetrics] = useState<PerformanceMetrics | null>(null);
  const [period, setPeriod] = useState('all_time');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadMetrics();
  }, [period]);

  const loadMetrics = async () => {
    setLoading(true);
    const data = await analyticsApi.getPerformance(period);
    setMetrics(data);
    setLoading(false);
  };

  if (loading) return <div>Loading performance...</div>;
  if (!metrics) return <div>No data available</div>;

  return (
    <div className="space-y-6">
      {/* Period selector */}
      <div className="flex gap-2">
        {['1m', '3m', '6m', 'ytd', '1y', 'all_time'].map((p) => (
          <button
            key={p}
            onClick={() => setPeriod(p)}
            className={`px-4 py-2 rounded ${
              period === p ? 'bg-blue-600 text-white' : 'bg-gray-100'
            }`}
          >
            {p.toUpperCase()}
          </button>
        ))}
      </div>

      {/* Key metrics */}
      <div className="grid grid-cols-4 gap-4">
        <MetricCard
          title="Total Return"
          value={`$${metrics.total_return.toLocaleString()}`}
          subtitle={`${metrics.total_return_percent}%`}
          positive={metrics.total_return > 0}
        />
        <MetricCard
          title="Win Rate"
          value={`${metrics.win_rate.toFixed(1)}%`}
          subtitle={`${metrics.winning_trades}W / ${metrics.losing_trades}L`}
        />
        <MetricCard
          title="Avg Win"
          value={`$${metrics.avg_win_amount.toLocaleString()}`}
          subtitle={`${metrics.avg_win_percent.toFixed(1)}%`}
          positive
        />
        <MetricCard
          title="Avg Loss"
          value={`$${metrics.avg_loss_amount.toLocaleString()}`}
          subtitle={`${metrics.avg_loss_percent.toFixed(1)}%`}
          positive={false}
        />
      </div>

      {/* Best/Worst trades */}
      <div className="grid grid-cols-2 gap-4">
        <TradeCard title="Best Trade" trade={metrics.best_trade} />
        <TradeCard title="Worst Trade" trade={metrics.worst_trade} />
      </div>

      {/* Chart placeholder */}
      <div className="bg-white p-6 rounded-lg shadow">
        <h3 className="text-lg font-semibold mb-4">Portfolio Value Over Time</h3>
        {/* Add chart component */}
      </div>
    </div>
  );
}
```

### 2. Update System Prompt

Update `backend/modules/agent/prompts.py`:

```python
FINCH_SYSTEM_PROMPT = """You are Finch, an AI investing performance coach.

Your mission: Help users become better investors by analyzing their actual trades, 
identifying patterns, and providing personalized insights and recommendations.

You are:
- **Personal**: You know their trading history, patterns, and tendencies
- **Educational**: You teach them WHY something worked or didn't work
- **Actionable**: You provide clear next steps, not just data
- **Honest**: You call out mistakes but also celebrate wins
- **Data-driven**: Every insight is backed by their actual trading data

Core Capabilities:
1. **Performance Analysis**: Calculate win rates, P&L, risk metrics (stocks only)
2. **Trade Grading**: Evaluate individual stock trades (A-F grades)
3. **Pattern Recognition**: Identify behavioral tendencies (panic selling, early exits, etc.)
4. **Opportunity Spotting**: Suggest stock trades matching their style + market conditions
5. **Portfolio Coaching**: Guide them to be more disciplined and profitable

**Important:** You analyze STOCK TRADES ONLY in this MVP version. If users ask about options, 
crypto, or other assets, politely explain that those features are coming in a future update.

Communication Style:
- Like a supportive coach, not a robot
- Use data but explain it simply
- Be direct about mistakes but encouraging about improvement
- Celebrate wins genuinely
- Use examples from their own trading history

When analyzing performance:
1. Always sync transaction history first if not recent
2. Look for patterns across multiple trades, not just individual ones
3. Compare to benchmarks (S&P 500)
4. Provide specific, actionable recommendations
5. Use their past winners to find similar opportunities

Example responses:
- "You've closed 23 trades this year with a 61% win rate - solid! But I noticed you're 
  selling winners after just 12 days on average, while your losers run for 45 days. 
  Let's flip that script."
- "Your tech picks are crushing it (avg +18%), but your healthcare trades are down -8%. 
  Maybe stick to what you know?"
- "NVDA is setting up similar to your TSLA trade from March (which netted you +$2,400). 
  Want to hear the setup?"

Remember: You're building a relationship with each user based on their unique trading journey.
"""
```

---

## ✅ Implementation Checklist

### Week 1: Database & Backend Core

- [ ] **Day 1-2: Database Setup**
  - [ ] Create Alembic migration for new tables
  - [ ] Add Transaction, PortfolioSnapshot, TradeAnalytics models to `models/db.py`
  - [ ] Add Pydantic models to `models/transactions.py`
  - [ ] Test migrations on dev database
  - [ ] Create CRUD operations in `crud/transactions.py`

- [ ] **Day 3-4: Transaction Sync**
  - [ ] Implement `TransactionSyncService` in `services/transaction_sync.py`
  - [ ] Test SnapTrade activities endpoint integration
  - [ ] Implement FIFO cost basis calculation
  - [ ] Add sync status tracking
  - [ ] Test with real SnapTrade data

- [ ] **Day 5-7: Analytics Engine**
  - [ ] Implement `AnalyticsService` in `services/analytics.py`
  - [ ] Build closed position matcher (FIFO accounting)
  - [ ] Calculate performance metrics (win rate, P&L, etc.)
  - [ ] Implement pattern detection algorithms
  - [ ] Write unit tests for calculations

### Week 2: Tools & AI Integration

- [ ] **Day 8-9: LLM Tools**
  - [ ] Add `get_transaction_history` tool
  - [ ] Add `analyze_portfolio_performance` tool
  - [ ] Add `analyze_specific_trade` tool
  - [ ] Add `identify_trading_patterns` tool
  - [ ] Update tool registry
  - [ ] Test tool execution

- [ ] **Day 10-11: API Routes**
  - [ ] Create `routes/analytics.py`
  - [ ] Add `/api/analytics/transactions/sync` endpoint
  - [ ] Add `/api/analytics/performance` endpoint
  - [ ] Add `/api/analytics/patterns` endpoint
  - [ ] Add `/api/analytics/trades/{trade_id}` endpoint
  - [ ] Test all endpoints with Postman/curl

- [ ] **Day 12-13: System Prompt & Agent**
  - [ ] Update system prompt in `prompts.py`
  - [ ] Add performance coaching persona
  - [ ] Test chat flows for common queries
  - [ ] Add example conversations
  - [ ] Fine-tune responses

- [ ] **Day 14: Testing & Polish**
  - [ ] End-to-end testing with real user flow
  - [ ] Performance optimization (query caching, etc.)
  - [ ] Error handling and edge cases
  - [ ] Logging and monitoring

### Week 3: Frontend & UX

- [ ] **Day 15-16: Performance Dashboard**
  - [ ] Create `PerformanceDashboard.tsx` component
  - [ ] Add metric cards for key stats
  - [ ] Integrate chart library (Recharts or Victory)
  - [ ] Build portfolio value over time chart
  - [ ] Add period selector (1M, 3M, YTD, etc.)

- [ ] **Day 17-18: Trade Journal**
  - [ ] Create `TradeJournal.tsx` component
  - [ ] Build transaction list view
  - [ ] Add trade detail modal
  - [ ] Show P&L with color coding
  - [ ] Add filters (symbol, date range, type)

- [ ] **Day 19: Chat Enhancements**
  - [ ] Add quick action buttons for performance queries
  - [ ] Update starter prompts
  - [ ] Add performance summary cards in chat
  - [ ] Improve markdown formatting for tables

- [ ] **Day 20: Navigation & Layout**
  - [ ] Add tabs: Dashboard | Chat | Journal
  - [ ] Update main layout
  - [ ] Add navigation menu
  - [ ] Mobile responsiveness

- [ ] **Day 21: Polish & QA**
  - [ ] UI/UX polish
  - [ ] Loading states
  - [ ] Empty states
  - [ ] Error states
  - [ ] Accessibility

### Week 4: Launch Prep

- [ ] **Day 22-23: Documentation**
  - [ ] User guide / walkthrough
  - [ ] API documentation updates
  - [ ] Feature screenshots
  - [ ] Video demo

- [ ] **Day 24-25: Testing**
  - [ ] User acceptance testing
  - [ ] Bug fixes
  - [ ] Performance testing
  - [ ] Security audit

- [ ] **Day 26-27: Deployment**
  - [ ] Production database migration
  - [ ] Deploy backend
  - [ ] Deploy frontend
  - [ ] Smoke tests in production

- [ ] **Day 28: Launch**
  - [ ] Soft launch to beta users
  - [ ] Monitor for issues
  - [ ] Gather feedback
  - [ ] Iterate based on feedback

---

## 🧪 Testing Strategy

### Unit Tests
- Transaction FIFO matching algorithm
- P&L calculations
- Performance metrics calculations
- Pattern detection logic

### Integration Tests
- SnapTrade API integration
- Database operations
- Tool execution flows
- API endpoints

### E2E Tests
- User connects brokerage → syncs transactions → views dashboard
- User asks "how am I doing?" → gets performance analysis
- User views trade journal → clicks trade → sees details

---

## 🚀 Success Metrics

### MVP Launch Goals (Week 4)
- ✅ 10 beta users successfully sync transactions
- ✅ 80% of users view performance dashboard
- ✅ Average session time > 5 minutes
- ✅ At least 20 performance queries via chat
- ✅ Zero critical bugs in production
- ✅ < 3 second load time for dashboard

### Product-Market Fit Signals (Weeks 5-12)
- 40%+ Week-1 retention
- 20%+ Week-4 retention
- NPS > 40
- Users share insights on social media
- Organic word-of-mouth growth
- Feature requests for advanced analytics

---

## 📊 Data Requirements

### Minimum Data Needed
- At least 10 completed trades (buy + sell pairs)
- Ideally 3+ months of history
- Multiple symbols (to detect patterns)

### Handling Edge Cases
- New users with no history: Show educational content, suggest connecting brokerage
- Users with only current holdings: Focus on current portfolio analysis, explain benefit of history
- Users with hundreds of trades: Pagination, filtering, aggregation
- **Users with options/crypto trades**: Skip those transactions, show message: "MVP supports stocks only. Options/crypto coming soon!"
- Mixed portfolios (stocks + options): Analyze stock trades only, note that some transactions were excluded

---

## 🔐 Privacy & Security

### Data Handling
- Never sell or share transaction data
- Encrypt sensitive data at rest
- Clear data retention policy
- GDPR compliance (allow data export/deletion)

### User Control
- Option to exclude specific trades from analysis
- Privacy mode (hide dollar amounts in screenshots)
- Data export in CSV format
- One-click account deletion

---

## 💡 Future Enhancements (Post-MVP)

### Phase 2: Opportunity Engine
- Personalized stock recommendations
- Multi-horizon trade ideas (day, swing, position, long-term)
- Integration with insider trades + Reddit sentiment
- Risk-aware position sizing

### Phase 3: Execution Platform
- Paper trading mode
- Real trade execution via SnapTrade
- Smart alerts and notifications
- Portfolio rebalancing

### Phase 4: Social & Gamification
- Anonymous leaderboards
- Trading achievements/badges
- Share insights on social media
- Compare with friends

### Phase 5: Advanced Analytics
- Tax loss harvesting suggestions
- Sector rotation signals
- Backtesting engine
- Risk analytics (beta, correlation)

### Phase 6: Multi-Asset Support
- Options trading analysis
  - Strategies (covered calls, spreads, etc.)
  - Greeks and risk metrics
  - Assignment/exercise tracking
- Crypto portfolio tracking
- ETF holdings analysis
- Mutual fund performance

---

## 🎯 Key Differentiators

**vs Robinhood/Fidelity:**
- AI-powered insights, not just data
- Personalized coaching based on YOUR trades
- Educational and actionable
- Cross-broker portfolio view

**vs Stock Screeners:**
- Recommendations match YOUR investing style
- Based on your historical winners
- Not generic picks

**vs Newsletter Services:**
- Personalized, not one-size-fits-all
- Interactive AI coach, not static content
- You own the relationship

**vs Portfolio Trackers:**
- Not just tracking, but IMPROVING
- Behavioral insights and pattern recognition
- Teaches you to be better

---

## 📱 Go-to-Market Strategy

### Beta Launch (Week 4)
- Invite 20-30 active traders from personal network
- Discord/Slack community for feedback
- Weekly check-ins to gather insights
- Iterate rapidly based on feedback

### Public Launch (Week 8)
- Product Hunt launch
- Reddit (r/investing, r/stocks, r/wallstreetbets)
- Twitter/X with demo video
- Partnerships with finance influencers

### Growth Tactics
- Shareable performance report cards
- "Roast my portfolio" viral angle
- Referral program (invite friends)
- Content marketing (trading psychology)

### Pricing
- **Free**: Basic performance dashboard, limited history
- **Pro ($19/mo)**: Full analytics, unlimited history, advanced patterns
- **Elite ($49/mo)**: Trade recommendations, paper trading, priority support

---

## 🔧 Tech Stack Summary

**Backend:**
- FastAPI (Python 3.12)
- PostgreSQL + SQLAlchemy
- SnapTrade API (brokerage data)
- Financial Modeling Prep (market data)
- Claude/GPT via LiteLLM
- OpenTelemetry (observability)

**Frontend:**
- Next.js 14 (React 18)
- TypeScript
- Tailwind CSS
- Recharts/Plotly (visualizations)
- SWR (data fetching)

**Infrastructure:**
- Supabase (auth + database)
- Vercel (frontend hosting)
- Railway/Render (backend hosting)
- GitHub Actions (CI/CD)

---

## 📞 Support & Resources

### Documentation
- API docs: `/docs` (FastAPI auto-generated)
- User guide: In-app walkthrough
- FAQ: Common questions about metrics

### Community
- Discord server for users
- Weekly AMA sessions
- Feature voting board

### Customer Support
- In-app chat support
- Email support@finch.app
- Response time: < 24 hours

---

## 🎉 MVP Complete When...

- [x] Users can connect brokerage accounts
- [x] Transactions sync automatically
- [x] Performance dashboard shows key metrics
- [x] Chat can analyze performance and answer questions
- [x] Trade journal shows all transactions
- [x] Behavioral patterns are detected and surfaced
- [x] System is deployed and accessible online
- [x] 10+ beta users have tested and provided feedback
- [x] Core user flow is smooth and bug-free

---

**Let's build something amazing! 🚀**

---

## Appendix: Sample Conversations

### Conversation 1: Performance Check
```
User: "How am I doing?"

Finch: "Let me pull up your stats! 📊

*[syncs transactions]*

Here's the breakdown:

**Overall Performance (All Time)**
• Total Return: **+$12,450** (18.2%)
• Win Rate: **63%** (24 wins, 14 losses)
• Profit Factor: 2.1 (you make $2.10 for every $1 you lose)

**Standout Stats:**
• Best Trade: NVDA (+$3,200, 67% gain) 🏆
• Worst Trade: PLTR (-$890, -22%)
• Avg Winner: +$520 (14 days hold)
• Avg Loser: -$245 (38 days hold)

**The Good:**
You're picking winners more than losers, and your profit factor is solid!

**Room to Improve:**
You're selling winners too early (14 days avg) but holding losers too long (38 days). 
If you flipped this, your returns could be 30-40% higher.

**Next Step:**
Want me to show you specific trades where you left money on the table?"
```

### Conversation 2: Trade Analysis
```
User: "Why did I lose money on TSLA?"

Finch: "Let me analyze your TSLA trades...

*[fetching transactions]*

I found 3 TSLA trades. Let me break down the most recent one:

**TSLA Trade (March 15 - March 28, 2024)**
• Entry: $245.50 (bought 25 shares = $6,137.50)
• Exit: $228.20 (sold 25 shares = $5,705)
• Loss: **-$432.50** (-7%)
• Hold Time: 13 days
• **Grade: D**

**What Happened:**
You bought on March 15th when TSLA had broken above $240 resistance. 
Good entry! But then:
- Day 3: Dropped to $235 (-4%)
- Day 7: Recovered to $252 (+2.7% gain)
- Day 10: Dropped again to $230
- Day 13: You sold at $228

**Optimal Exit:**
If you'd sold on Day 7 at $252, you'd have made **+$162.50** instead of losing $432.

**What You Could've Done Better:**
1. Set a stop loss at $235 (would've saved you $100)
2. Taken profits at $252 when it hit the news high
3. The stock was range-bound $220-$250 - this was a swing trade, not a trend

**Pattern I'm Seeing:**
This is the 3rd time you've held through a drawdown hoping it recovers. 
Sometimes it's better to cut losses early and redeploy capital elsewhere.

Want me to suggest a better strategy for volatile stocks like TSLA?"
```

---

**This is your roadmap to MVP. Now let's execute! 💪**

