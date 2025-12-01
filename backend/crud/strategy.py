"""
CRUD operations for trading strategies
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from datetime import datetime
import json

from models.db import TradingStrategyDB, StrategyBacktestDB, StrategySignalDB, StrategyPerformanceDB
from models.strategy import (
    TradingStrategy, StrategyBacktest, StrategySignal, 
    StrategyPerformance, StrategyComparison
)


def create_strategy(db: Session, strategy: TradingStrategy) -> TradingStrategyDB:
    """Create a new trading strategy"""
    db_strategy = TradingStrategyDB(
        id=strategy.id,
        user_id=strategy.user_id,
        name=strategy.name,
        description=strategy.description,
        natural_language_input=strategy.natural_language_input,
        strategy_definition=strategy.model_dump(mode='json'),
        is_active=strategy.is_active,
        created_at=strategy.created_at,
        updated_at=strategy.updated_at
    )
    
    db.add(db_strategy)
    db.commit()
    db.refresh(db_strategy)
    
    # Also create performance tracker
    perf = StrategyPerformanceDB(
        strategy_id=strategy.id,
        user_id=strategy.user_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(perf)
    db.commit()
    
    return db_strategy


def get_strategy(db: Session, strategy_id: str) -> Optional[TradingStrategy]:
    """Get a strategy by ID"""
    db_strategy = db.query(TradingStrategyDB).filter(
        TradingStrategyDB.id == strategy_id
    ).first()
    
    if not db_strategy:
        return None
    
    return TradingStrategy(**db_strategy.strategy_definition)


def get_user_strategies(
    db: Session,
    user_id: str,
    active_only: bool = True
) -> List[TradingStrategy]:
    """Get all strategies for a user"""
    query = db.query(TradingStrategyDB).filter(
        TradingStrategyDB.user_id == user_id
    )
    
    if active_only:
        query = query.filter(TradingStrategyDB.is_active == True)
    
    db_strategies = query.order_by(TradingStrategyDB.created_at.desc()).all()
    
    return [TradingStrategy(**s.strategy_definition) for s in db_strategies]


def update_strategy(db: Session, strategy: TradingStrategy) -> TradingStrategyDB:
    """Update an existing strategy"""
    db_strategy = db.query(TradingStrategyDB).filter(
        TradingStrategyDB.id == strategy.id
    ).first()
    
    if not db_strategy:
        raise ValueError(f"Strategy {strategy.id} not found")
    
    strategy.updated_at = datetime.utcnow()
    
    db_strategy.name = strategy.name
    db_strategy.description = strategy.description
    db_strategy.strategy_definition = strategy.model_dump(mode='json')
    db_strategy.is_active = strategy.is_active
    db_strategy.updated_at = strategy.updated_at
    
    db.commit()
    db.refresh(db_strategy)
    
    return db_strategy


def delete_strategy(db: Session, strategy_id: str) -> bool:
    """Soft delete a strategy (mark as inactive)"""
    db_strategy = db.query(TradingStrategyDB).filter(
        TradingStrategyDB.id == strategy_id
    ).first()
    
    if not db_strategy:
        return False
    
    db_strategy.is_active = False
    db_strategy.updated_at = datetime.utcnow()
    db.commit()
    
    return True


def save_backtest(db: Session, backtest: StrategyBacktest) -> StrategyBacktestDB:
    """Save backtest results"""
    db_backtest = StrategyBacktestDB(
        backtest_id=backtest.backtest_id,
        strategy_id=backtest.strategy_id,
        start_date=backtest.start_date,
        end_date=backtest.end_date,
        backtest_results=backtest.model_dump(mode='json'),
        created_at=backtest.created_at
    )
    
    db.add(db_backtest)
    db.commit()
    db.refresh(db_backtest)
    
    return db_backtest


def get_strategy_backtests(
    db: Session,
    strategy_id: str
) -> List[StrategyBacktest]:
    """Get all backtests for a strategy"""
    db_backtests = db.query(StrategyBacktestDB).filter(
        StrategyBacktestDB.strategy_id == strategy_id
    ).order_by(StrategyBacktestDB.created_at.desc()).all()
    
    return [StrategyBacktest(**b.backtest_results) for b in db_backtests]


def get_latest_backtest(
    db: Session,
    strategy_id: str
) -> Optional[StrategyBacktest]:
    """Get the most recent backtest for a strategy"""
    db_backtest = db.query(StrategyBacktestDB).filter(
        StrategyBacktestDB.strategy_id == strategy_id
    ).order_by(StrategyBacktestDB.created_at.desc()).first()
    
    if not db_backtest:
        return None
    
    return StrategyBacktest(**db_backtest.backtest_results)


def save_signal(db: Session, signal: StrategySignal) -> StrategySignalDB:
    """Save a strategy signal"""
    db_signal = StrategySignalDB(
        signal_id=signal.signal_id,
        strategy_id=signal.strategy_id,
        ticker=signal.ticker,
        signal_type=signal.signal_type,
        generated_at=signal.generated_at,
        price_at_signal=signal.price_at_signal,
        confidence_score=signal.confidence_score,
        reasoning=signal.reasoning,
        data_snapshot=signal.data_snapshot,
        user_acted=signal.user_acted,
        outcome=signal.outcome
    )
    
    db.add(db_signal)
    db.commit()
    db.refresh(db_signal)
    
    # Update strategy performance last_signal_date
    perf = db.query(StrategyPerformanceDB).filter(
        StrategyPerformanceDB.strategy_id == signal.strategy_id
    ).first()
    
    if perf:
        perf.signals_generated += 1
        perf.last_signal_date = signal.generated_at
        perf.updated_at = datetime.utcnow()
        db.commit()
    
    return db_signal


def get_strategy_signals(
    db: Session,
    strategy_id: str,
    limit: int = 50
) -> List[StrategySignal]:
    """Get recent signals for a strategy"""
    db_signals = db.query(StrategySignalDB).filter(
        StrategySignalDB.strategy_id == strategy_id
    ).order_by(StrategySignalDB.generated_at.desc()).limit(limit).all()
    
    return [StrategySignal(**{
        'signal_id': s.signal_id,
        'strategy_id': s.strategy_id,
        'ticker': s.ticker,
        'signal_type': s.signal_type,
        'generated_at': s.generated_at,
        'price_at_signal': float(s.price_at_signal),
        'confidence_score': s.confidence_score,
        'reasoning': s.reasoning,
        'data_snapshot': s.data_snapshot,
        'user_acted': s.user_acted,
        'outcome': s.outcome
    }) for s in db_signals]


def get_strategy_performance(
    db: Session,
    strategy_id: str
) -> Optional[StrategyPerformance]:
    """Get performance tracking for a strategy"""
    db_perf = db.query(StrategyPerformanceDB).filter(
        StrategyPerformanceDB.strategy_id == strategy_id
    ).first()
    
    if not db_perf:
        return None
    
    return StrategyPerformance(
        id=db_perf.id,
        strategy_id=db_perf.strategy_id,
        user_id=db_perf.user_id,
        signals_generated=db_perf.signals_generated,
        signals_acted_on=db_perf.signals_acted_on,
        actual_trades=db_perf.actual_trades,
        actual_wins=db_perf.actual_wins,
        actual_losses=db_perf.actual_losses,
        actual_return_pct=db_perf.actual_return_pct,
        hypothetical_trades=db_perf.hypothetical_trades,
        hypothetical_return_pct=db_perf.hypothetical_return_pct,
        last_signal_date=db_perf.last_signal_date,
        created_at=db_perf.created_at,
        updated_at=db_perf.updated_at
    )


def compare_user_strategies(
    db: Session,
    user_id: str
) -> List[StrategyComparison]:
    """Get comparison data for all user strategies"""
    strategies = get_user_strategies(db, user_id, active_only=True)
    
    comparisons = []
    for strategy in strategies:
        perf = get_strategy_performance(db, strategy.id)
        
        if perf:
            comparisons.append(StrategyComparison(
                strategy_id=strategy.id,
                strategy_name=strategy.name,
                timeframe=strategy.timeframe,
                signals_generated=perf.signals_generated,
                win_rate=(perf.actual_wins / perf.actual_trades * 100) if perf.actual_trades > 0 else None,
                actual_return_pct=perf.actual_return_pct,
                hypothetical_return_pct=perf.hypothetical_return_pct,
                last_signal=perf.last_signal_date,
                is_active=strategy.is_active
            ))
    
    # Sort by actual return (or hypothetical if no actual trades)
    comparisons.sort(
        key=lambda x: x.actual_return_pct if x.actual_return_pct else x.hypothetical_return_pct,
        reverse=True
    )
    
    return comparisons

