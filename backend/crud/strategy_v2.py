"""
CRUD operations for V2 strategies - Clean & Simple
"""
from sqlalchemy.orm import Session
from models.db import TradingStrategyV2DB, StrategyDecisionDB, StrategyPositionDB, StrategyBudgetDB
from models.strategy_v2 import TradingStrategyV2, StrategyDecision, StrategyPosition, StrategyBudget
from typing import List, Optional
from datetime import datetime, date, timedelta
import logging

logger = logging.getLogger(__name__)


def create_strategy(db: Session, strategy: TradingStrategyV2) -> TradingStrategyV2DB:
    """Create a new V2 strategy"""
    db_strategy = TradingStrategyV2DB(
        id=strategy.id,
        user_id=strategy.user_id,
        chat_id=strategy.chat_id,
        name=strategy.name,
        description=strategy.description,
        candidate_source=strategy.candidate_source.model_dump(),
        screening_rules=[r.model_dump() for r in strategy.screening_rules],
        management_rules=[r.model_dump() for r in strategy.management_rules] if strategy.management_rules else [],
        risk_parameters=strategy.risk_parameters.model_dump(),
        is_active=strategy.is_active,
        created_at=strategy.created_at,
        updated_at=strategy.updated_at
    )
    
    db.add(db_strategy)
    db.commit()
    db.refresh(db_strategy)
    
    return db_strategy


def get_strategy(db: Session, strategy_id: str) -> Optional[TradingStrategyV2]:
    """Get a strategy by ID"""
    db_strategy = db.query(TradingStrategyV2DB).filter(
        TradingStrategyV2DB.id == strategy_id
    ).first()
    
    if not db_strategy:
        return None
    
    from models.strategy_v2 import StrategyRule, RiskParameters, CandidateSource
    
    return TradingStrategyV2(
        id=db_strategy.id,
        user_id=db_strategy.user_id,
        chat_id=db_strategy.chat_id,
        name=db_strategy.name,
        description=db_strategy.description,
        candidate_source=CandidateSource(**db_strategy.candidate_source),
        screening_rules=[StrategyRule(**rule) for rule in db_strategy.screening_rules],
        management_rules=[StrategyRule(**rule) for rule in (db_strategy.management_rules or [])],
        risk_parameters=RiskParameters(**db_strategy.risk_parameters),
        is_active=db_strategy.is_active,
        created_at=db_strategy.created_at,
        updated_at=db_strategy.updated_at
    )


def get_user_strategies(db: Session, user_id: str, active_only: bool = True) -> List[TradingStrategyV2]:
    """Get all strategies for a user (across all chats)"""
    query = db.query(TradingStrategyV2DB).filter(
        TradingStrategyV2DB.user_id == user_id
    )
    
    if active_only:
        query = query.filter(TradingStrategyV2DB.is_active == True)
    
    db_strategies = query.order_by(TradingStrategyV2DB.created_at.desc()).all()
    
    from models.strategy_v2 import StrategyRule, RiskParameters, CandidateSource
    
    return [
        TradingStrategyV2(
            id=s.id,
            user_id=s.user_id,
            chat_id=s.chat_id,
            name=s.name,
            description=s.description,
            candidate_source=CandidateSource(**s.candidate_source),
            screening_rules=[StrategyRule(**rule) for rule in s.screening_rules],
            management_rules=[StrategyRule(**rule) for rule in (s.management_rules or [])],
            risk_parameters=RiskParameters(**s.risk_parameters),
            is_active=s.is_active,
            created_at=s.created_at,
            updated_at=s.updated_at
        )
        for s in db_strategies
    ]


def get_chat_strategies(db: Session, chat_id: str, active_only: bool = True) -> List[TradingStrategyV2]:
    """Get all strategies for a specific chat"""
    query = db.query(TradingStrategyV2DB).filter(
        TradingStrategyV2DB.chat_id == chat_id
    )
    
    if active_only:
        query = query.filter(TradingStrategyV2DB.is_active == True)
    
    db_strategies = query.order_by(TradingStrategyV2DB.created_at.desc()).all()
    
    from models.strategy_v2 import StrategyRule, RiskParameters, CandidateSource
    
    return [
        TradingStrategyV2(
            id=s.id,
            user_id=s.user_id,
            chat_id=s.chat_id,
            name=s.name,
            description=s.description,
            candidate_source=CandidateSource(**s.candidate_source),
            screening_rules=[StrategyRule(**rule) for rule in s.screening_rules],
            management_rules=[StrategyRule(**rule) for rule in (s.management_rules or [])],
            risk_parameters=RiskParameters(**s.risk_parameters),
            is_active=s.is_active,
            created_at=s.created_at,
            updated_at=s.updated_at
        )
        for s in db_strategies
    ]


def update_strategy(db: Session, strategy: TradingStrategyV2) -> TradingStrategyV2DB:
    """Update a strategy"""
    db_strategy = db.query(TradingStrategyV2DB).filter(
        TradingStrategyV2DB.id == strategy.id
    ).first()
    
    if not db_strategy:
        raise ValueError(f"Strategy {strategy.id} not found")
    
    db_strategy.name = strategy.name
    db_strategy.description = strategy.description
    db_strategy.candidate_source = strategy.candidate_source.model_dump()
    db_strategy.screening_rules = [r.model_dump() for r in strategy.screening_rules]
    db_strategy.management_rules = [r.model_dump() for r in strategy.management_rules] if strategy.management_rules else []
    db_strategy.risk_parameters = strategy.risk_parameters.model_dump()
    db_strategy.is_active = strategy.is_active
    db_strategy.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(db_strategy)
    
    return db_strategy


def delete_strategy(db: Session, strategy_id: str) -> bool:
    """Soft delete a strategy"""
    db_strategy = db.query(TradingStrategyV2DB).filter(
        TradingStrategyV2DB.id == strategy_id
    ).first()
    
    if not db_strategy:
        return False
    
    db_strategy.is_active = False
    db_strategy.updated_at = datetime.utcnow()
    
    db.commit()
    
    return True


# Strategy Decision CRUD

def save_decision(db: Session, decision: StrategyDecision, chat_id: str) -> StrategyDecisionDB:
    """Save a strategy decision"""
    db_decision = StrategyDecisionDB(
        id=decision.decision_id,
        strategy_id=decision.strategy_id,
        chat_id=chat_id,
        ticker=decision.ticker,
        timestamp=decision.timestamp,
        action=decision.action,
        confidence=decision.confidence,
        reasoning=decision.reasoning,
        rule_results=decision.rule_results,
        data_snapshot=decision.data_snapshot,
        current_price=decision.current_price
    )
    
    db.add(db_decision)
    db.commit()
    db.refresh(db_decision)
    
    return db_decision


def get_strategy_decisions(
    db: Session,
    strategy_id: str,
    days: int = 7,
    action_filter: Optional[str] = None
) -> List[StrategyDecision]:
    """Get recent decisions for a strategy"""
    from datetime import timedelta
    
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    query = db.query(StrategyDecisionDB).filter(
        StrategyDecisionDB.strategy_id == strategy_id,
        StrategyDecisionDB.timestamp >= cutoff
    )
    
    if action_filter:
        query = query.filter(StrategyDecisionDB.action == action_filter)
    
    db_decisions = query.order_by(StrategyDecisionDB.timestamp.desc()).all()
    
    return [
        StrategyDecision(
            decision_id=d.id,
            strategy_id=d.strategy_id,
            ticker=d.ticker,
            timestamp=d.timestamp,
            action=d.action,
            confidence=d.confidence,
            reasoning=d.reasoning,
            rule_results=d.rule_results,
            data_snapshot=d.data_snapshot,
            current_price=d.current_price
        )
        for d in db_decisions
    ]


# Budget CRUD

def create_budget(db: Session, budget: StrategyBudget) -> StrategyBudgetDB:
    """Create strategy budget"""
    db_budget = StrategyBudgetDB(
        strategy_id=budget.strategy_id,
        user_id=budget.user_id,
        chat_id=budget.chat_id,
        total_budget=budget.total_budget,
        cash_available=budget.cash_available,
        position_value=budget.position_value,
        updated_at=budget.updated_at
    )
    
    db.add(db_budget)
    db.commit()
    db.refresh(db_budget)
    
    return db_budget


def get_budget(db: Session, strategy_id: str) -> Optional[StrategyBudget]:
    """Get strategy budget"""
    db_budget = db.query(StrategyBudgetDB).filter(
        StrategyBudgetDB.strategy_id == strategy_id
    ).first()
    
    if not db_budget:
        return None
    
    return StrategyBudget(
        strategy_id=db_budget.strategy_id,
        user_id=db_budget.user_id,
        chat_id=db_budget.chat_id,
        total_budget=db_budget.total_budget,
        cash_available=db_budget.cash_available,
        position_value=db_budget.position_value,
        updated_at=db_budget.updated_at
    )


# Position CRUD

def create_position(db: Session, position: StrategyPosition) -> StrategyPositionDB:
    """Create a position"""
    db_position = StrategyPositionDB(
        id=position.position_id,
        strategy_id=position.strategy_id,
        user_id=position.user_id,
        chat_id=position.chat_id,
        ticker=position.ticker,
        shares=position.shares,
        entry_price=position.entry_price,
        entry_date=position.entry_date,
        entry_decision_id=position.entry_decision_id,
        current_price=position.current_price,
        current_value=position.current_value,
        pnl=position.pnl,
        pnl_pct=position.pnl_pct,
        days_held=position.days_held,
        is_open=position.is_open,
        created_at=position.created_at,
        updated_at=position.updated_at
    )
    
    db.add(db_position)
    db.commit()
    db.refresh(db_position)
    
    return db_position


def get_positions(db: Session, strategy_id: str, open_only: bool = True) -> List[StrategyPosition]:
    """Get strategy positions"""
    query = db.query(StrategyPositionDB).filter(
        StrategyPositionDB.strategy_id == strategy_id
    )
    
    if open_only:
        query = query.filter(StrategyPositionDB.is_open == True)
    
    db_positions = query.all()
    
    # Update position metrics (current price, P&L, days held)
    for p in db_positions:
        if p.is_open:
            p.days_held = (date.today() - p.entry_date).days
            # current_price should be updated by executor
            if p.current_price > 0:
                p.current_value = p.shares * p.current_price
                p.pnl = p.current_value - (p.shares * p.entry_price)
                p.pnl_pct = (p.pnl / (p.shares * p.entry_price)) * 100
    
    db.commit()
    
    return [
        StrategyPosition(
            position_id=p.id,
            strategy_id=p.strategy_id,
            user_id=p.user_id,
            chat_id=p.chat_id,
            ticker=p.ticker,
            shares=p.shares,
            entry_price=p.entry_price,
            entry_date=p.entry_date,
            entry_decision_id=p.entry_decision_id,
            current_price=p.current_price,
            current_value=p.current_value,
            pnl=p.pnl,
            pnl_pct=p.pnl_pct,
            days_held=p.days_held,
            exit_date=p.exit_date,
            exit_price=p.exit_price,
            exit_decision_id=p.exit_decision_id,
            is_open=p.is_open,
            created_at=p.created_at,
            updated_at=p.updated_at
        )
        for p in db_positions
    ]


def update_position_price(db: Session, position_id: str, current_price: float):
    """Update position's current price and recalculate metrics"""
    db_position = db.query(StrategyPositionDB).filter(
        StrategyPositionDB.id == position_id
    ).first()
    
    if not db_position:
        raise ValueError(f"Position {position_id} not found")
    
    db_position.current_price = current_price
    db_position.current_value = db_position.shares * current_price
    db_position.pnl = db_position.current_value - (db_position.shares * db_position.entry_price)
    db_position.pnl_pct = (db_position.pnl / (db_position.shares * db_position.entry_price)) * 100
    db_position.days_held = (date.today() - db_position.entry_date).days
    db_position.updated_at = datetime.utcnow()
    
    db.commit()


def close_position(db: Session, position_id: str, exit_price: float, exit_decision_id: str):
    """Close a position"""
    db_position = db.query(StrategyPositionDB).filter(
        StrategyPositionDB.id == position_id
    ).first()
    
    if not db_position:
        raise ValueError(f"Position {position_id} not found")
    
    db_position.exit_date = date.today()
    db_position.exit_price = exit_price
    db_position.exit_decision_id = exit_decision_id
    db_position.is_open = False
    db_position.updated_at = datetime.utcnow()
    
    # Update budget (return cash)
    db_budget = db.query(StrategyBudgetDB).filter(
        StrategyBudgetDB.strategy_id == db_position.strategy_id
    ).first()
    
    if db_budget:
        exit_value = db_position.shares * exit_price
        db_budget.cash_available += exit_value
        db_budget.position_value -= db_position.current_value
        db_budget.updated_at = datetime.utcnow()
    
    db.commit()

