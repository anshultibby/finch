"""
CRUD operations for V2 strategies
"""
from sqlalchemy.orm import Session
from models.db import TradingStrategyV2DB, StrategyDecisionDB, ForwardTestDB
from models.strategy_v2 import TradingStrategyV2, StrategyDecision, ForwardTest
from typing import List, Optional
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)


def create_strategy(db: Session, strategy: TradingStrategyV2) -> TradingStrategyV2DB:
    """Create a new V2 strategy"""
    db_strategy = TradingStrategyV2DB(
        id=strategy.id,
        user_id=strategy.user_id,
        name=strategy.name,
        description=strategy.description,
        rules=strategy.model_dump()["rules"],  # Store as JSONB
        risk_parameters=strategy.risk_parameters.model_dump(),
        stock_universe=strategy.stock_universe,
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
    
    # Convert to Pydantic model
    from models.strategy_v2 import StrategyRule, RiskParameters
    
    return TradingStrategyV2(
        id=db_strategy.id,
        user_id=db_strategy.user_id,
        name=db_strategy.name,
        description=db_strategy.description,
        rules=[StrategyRule(**rule) for rule in db_strategy.rules],
        risk_parameters=RiskParameters(**db_strategy.risk_parameters),
        stock_universe=db_strategy.stock_universe,
        is_active=db_strategy.is_active,
        created_at=db_strategy.created_at,
        updated_at=db_strategy.updated_at
    )


def get_user_strategies(db: Session, user_id: str, active_only: bool = True) -> List[TradingStrategyV2]:
    """Get all strategies for a user"""
    query = db.query(TradingStrategyV2DB).filter(
        TradingStrategyV2DB.user_id == user_id
    )
    
    if active_only:
        query = query.filter(TradingStrategyV2DB.is_active == True)
    
    db_strategies = query.order_by(TradingStrategyV2DB.created_at.desc()).all()
    
    from models.strategy_v2 import StrategyRule, RiskParameters
    
    return [
        TradingStrategyV2(
            id=s.id,
            user_id=s.user_id,
            name=s.name,
            description=s.description,
            rules=[StrategyRule(**rule) for rule in s.rules],
            risk_parameters=RiskParameters(**s.risk_parameters),
            stock_universe=s.stock_universe,
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
    db_strategy.rules = strategy.model_dump()["rules"]
    db_strategy.risk_parameters = strategy.risk_parameters.model_dump()
    db_strategy.stock_universe = strategy.stock_universe
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

def save_decision(db: Session, decision: StrategyDecision) -> StrategyDecisionDB:
    """Save a strategy decision"""
    db_decision = StrategyDecisionDB(
        id=decision.decision_id,
        strategy_id=decision.strategy_id,
        ticker=decision.ticker,
        timestamp=decision.timestamp,
        action=decision.action,
        confidence=decision.confidence,
        reasoning=decision.reasoning,
        rule_results=decision.rule_results,
        data_snapshot=decision.data_snapshot,
        current_price=decision.current_price,
        user_acted=False,
        outcome=None
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


def record_user_action(db: Session, decision_id: str, acted: bool, outcome: Optional[dict] = None):
    """Record whether user acted on a decision"""
    db_decision = db.query(StrategyDecisionDB).filter(
        StrategyDecisionDB.id == decision_id
    ).first()
    
    if db_decision:
        db_decision.user_acted = acted
        if outcome:
            db_decision.outcome = outcome
        db.commit()


# Forward Test CRUD

def create_forward_test(db: Session, forward_test: ForwardTest) -> ForwardTestDB:
    """Create a new forward test"""
    db_test = ForwardTestDB(
        id=forward_test.test_id,
        strategy_id=forward_test.strategy_id,
        user_id=forward_test.user_id,
        start_date=forward_test.start_date,
        is_active=forward_test.is_active,
        total_signals=forward_test.total_signals,
        signals_acted_on=forward_test.signals_acted_on,
        hypothetical_pnl=forward_test.hypothetical_pnl,
        actual_pnl=forward_test.actual_pnl,
        created_at=forward_test.created_at,
        updated_at=forward_test.updated_at
    )
    
    db.add(db_test)
    db.commit()
    db.refresh(db_test)
    
    return db_test


def get_active_forward_tests(db: Session, user_id: Optional[str] = None) -> List[ForwardTest]:
    """Get all active forward tests"""
    query = db.query(ForwardTestDB).filter(ForwardTestDB.is_active == True)
    
    if user_id:
        query = query.filter(ForwardTestDB.user_id == user_id)
    
    db_tests = query.all()
    
    return [
        ForwardTest(
            test_id=t.id,
            strategy_id=t.strategy_id,
            user_id=t.user_id,
            start_date=t.start_date,
            is_active=t.is_active,
            total_signals=t.total_signals,
            signals_acted_on=t.signals_acted_on,
            hypothetical_pnl=t.hypothetical_pnl,
            actual_pnl=t.actual_pnl,
            created_at=t.created_at,
            updated_at=t.updated_at
        )
        for t in db_tests
    ]

