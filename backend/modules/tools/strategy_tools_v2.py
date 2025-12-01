"""
V2 Strategy Tools - Modern LLM-native trading strategies
"""
from modules.tools import tool
from modules.agent.context import AgentContext
from models.sse import SSEEvent
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)


# Pydantic models for tool parameters

class DataSourceInput(BaseModel):
    type: str = Field(..., description="Source type: fmp, reddit, calculated, portfolio")
    endpoint: str = Field(..., description="API endpoint name")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="API parameters")


class StrategyRuleInput(BaseModel):
    order: int = Field(..., description="Execution order (1-based)")
    description: str = Field(..., description="What this rule does")
    data_sources: List[DataSourceInput] = Field(default_factory=list)
    decision_logic: str = Field(..., description="How to interpret data and decide")
    weight: float = Field(1.0, ge=0, le=1, description="Rule importance 0-1")


class RiskParametersInput(BaseModel):
    position_size_pct: float = Field(5.0, gt=0, le=100)
    max_positions: int = Field(5, gt=0)
    stop_loss_pct: Optional[float] = Field(None, gt=0)
    take_profit_pct: Optional[float] = Field(None, gt=0)
    max_hold_days: Optional[int] = Field(None, gt=0)


class CreateStrategyV2Params(BaseModel):
    name: str
    description: str
    rules: List[StrategyRuleInput]
    risk_parameters: RiskParametersInput
    stock_universe: Optional[List[str]] = None


# Tools

@tool(
    name="create_trading_strategy",
    description="""Create a modern rule-based trading strategy.

A strategy consists of RULES - natural language descriptions that guide LLM decision-making.
Each rule can fetch data and contribute to the final BUY/SELL/HOLD decision.

IMPORTANT: Structure the rules properly:
1. Early rules should filter/validate (use "SKIP" to reject tickers)
2. Middle rules should analyze data and provide signals (BULLISH/BEARISH/NEUTRAL)
3. Final rule should aggregate and decide (BUY/SELL/HOLD)

Example strategy:
{
    "name": "Tech Growth + Sentiment",
    "description": "Buy tech stocks with strong fundamentals and positive buzz",
    "rules": [
        {
            "order": 1,
            "description": "Verify it's a technology stock",
            "data_sources": [
                {"type": "fmp", "endpoint": "company-profile", "parameters": {}}
            ],
            "decision_logic": "Check if sector is 'Technology'. If not, SKIP this stock.",
            "weight": 0.2
        },
        {
            "order": 2,
            "description": "Check revenue growth (fundamental signal)",
            "data_sources": [
                {"type": "fmp", "endpoint": "income-statement", "parameters": {"period": "annual", "limit": 2}}
            ],
            "decision_logic": "Calculate YoY revenue growth. If >20%, signal is BULLISH (value: 0.8). If <0%, BEARISH (value: 0.2). Otherwise NEUTRAL (value: 0.5).",
            "weight": 0.4
        },
        {
            "order": 3,
            "description": "Check Reddit sentiment (social signal)",
            "data_sources": [
                {"type": "reddit", "endpoint": "ticker_sentiment", "parameters": {"days": 7}}
            ],
            "decision_logic": "If sentiment score >0.7, BULLISH. If <0.3, BEARISH. Otherwise NEUTRAL.",
            "weight": 0.4
        }
    ],
    "risk_parameters": {
        "position_size_pct": 5.0,
        "max_positions": 5,
        "stop_loss_pct": 10.0,
        "take_profit_pct": 25.0
    }
}

Available data sources:
FMP: company-profile, income-statement, balance-sheet, cash-flow, insider-trading, quote, price-history, key-metrics
Reddit: ticker_sentiment, trending_stocks
Calculated: rsi, moving_average, volume_analysis
""",
    category="strategy"
)
async def create_trading_strategy_v2(
    *,
    context: AgentContext,
    params: CreateStrategyV2Params
):
    """Create a rule-based trading strategy"""
    from models.strategy_v2 import TradingStrategyV2, StrategyRule, DataSource, RiskParameters
    from crud.strategy_v2 import create_strategy
    from database import SessionLocal
    import uuid
    
    yield SSEEvent(
        event="tool_status",
        data={"status": "creating", "message": f"Creating strategy: {params.name}"}
    )
    
    try:
        # Convert to domain model
        strategy = TradingStrategyV2(
            id=str(uuid.uuid4()),
            user_id=context.user_id,
            name=params.name,
            description=params.description,
            rules=[
                StrategyRule(
                    order=rule.order,
                    description=rule.description,
                    data_sources=[
                        DataSource(**ds.model_dump())
                        for ds in rule.data_sources
                    ],
                    decision_logic=rule.decision_logic,
                    weight=rule.weight
                )
                for rule in params.rules
            ],
            risk_parameters=RiskParameters(**params.risk_parameters.model_dump()),
            stock_universe=params.stock_universe,
            is_active=True
        )
        
        # Save to database
        with SessionLocal() as db:
            db_strategy = create_strategy(db, strategy)
        
        yield {
            "success": True,
            "strategy_id": strategy.id,
            "strategy_name": strategy.name,
            "description": strategy.description,
            "num_rules": len(strategy.rules),
            "message": f"✓ Strategy '{params.name}' created with {len(strategy.rules)} rules! Use test_strategy to try it on a ticker."
        }
        
    except Exception as e:
        logger.error(f"Error creating strategy: {str(e)}", exc_info=True)
        yield {
            "success": False,
            "error": f"Failed to create strategy: {str(e)}",
            "message": f"Error: {str(e)}"
        }


@tool(
    name="test_strategy",
    description="""Test a strategy on a specific ticker to see how it would decide.

This executes the strategy's rules step-by-step and shows:
- What data was fetched
- How each rule evaluated
- The final decision (BUY/SELL/HOLD/SKIP)
- Full reasoning

Perfect for validating strategy logic before running it on many stocks.""",
    category="strategy"
)
async def test_strategy(
    *,
    context: AgentContext,
    strategy_id: str,
    ticker: str
):
    """Test a strategy on one ticker"""
    from crud.strategy_v2 import get_strategy
    from services.strategy_executor import StrategyExecutor
    from database import SessionLocal
    
    yield SSEEvent(
        event="tool_status",
        data={"status": "testing", "message": f"Testing strategy on {ticker}..."}
    )
    
    try:
        # Get strategy
        with SessionLocal() as db:
            strategy = get_strategy(db, strategy_id)
        
        if not strategy:
            yield {
                "success": False,
                "error": f"Strategy {strategy_id} not found"
            }
            return
        
        # Check ownership
        if strategy.user_id != context.user_id:
            yield {
                "success": False,
                "error": "You don't have permission to access this strategy"
            }
            return
        
        # Execute strategy
        executor = StrategyExecutor()
        decision = await executor.execute_strategy(strategy, ticker)
        
        # Format response
        yield {
            "success": True,
            "ticker": ticker,
            "strategy_name": strategy.name,
            "decision": {
                "action": decision.action,
                "confidence": decision.confidence,
                "current_price": decision.current_price,
                "reasoning": decision.reasoning
            },
            "rule_breakdown": decision.rule_results,
            "message": f"✓ Strategy decided: {decision.action} {ticker} (confidence: {decision.confidence}%)"
        }
        
    except Exception as e:
        logger.error(f"Error testing strategy: {str(e)}", exc_info=True)
        yield {
            "success": False,
            "error": f"Failed to test strategy: {str(e)}",
            "message": f"Error: {str(e)}"
        }


@tool(
    name="scan_with_strategy",
    description="""Scan multiple tickers with a strategy to find trading opportunities.

Executes the strategy on each ticker and returns only BUY/SELL signals.
Useful for finding opportunities across many stocks.

Example: Scan the top 20 tech stocks to see which ones your strategy recommends.""",
    category="strategy"
)
async def scan_with_strategy(
    *,
    context: AgentContext,
    strategy_id: str,
    tickers: List[str],
    max_results: int = 10
):
    """Scan multiple tickers with a strategy"""
    from crud.strategy_v2 import get_strategy, save_decision
    from services.strategy_executor import StrategyExecutor
    from database import SessionLocal
    
    yield SSEEvent(
        event="tool_status",
        data={"status": "scanning", "message": f"Scanning {len(tickers)} tickers..."}
    )
    
    try:
        # Get strategy
        with SessionLocal() as db:
            strategy = get_strategy(db, strategy_id)
            
            if not strategy:
                yield {
                    "success": False,
                    "error": f"Strategy {strategy_id} not found"
                }
                return
            
            # Check ownership
            if strategy.user_id != context.user_id:
                yield {
                    "success": False,
                    "error": "You don't have permission to access this strategy"
                }
                return
            
            # Execute strategy on each ticker
            executor = StrategyExecutor()
            signals = []
            
            for ticker in tickers[:50]:  # Limit to 50 tickers max
                try:
                    decision = await executor.execute_strategy(strategy, ticker)
                    
                    # Save decision
                    save_decision(db, decision)
                    
                    # Only include BUY/SELL signals
                    if decision.action in ["BUY", "SELL"]:
                        signals.append({
                            "ticker": ticker,
                            "action": decision.action,
                            "confidence": decision.confidence,
                            "current_price": decision.current_price,
                            "reasoning": decision.reasoning
                        })
                    
                    # Stream progress
                    if len(signals) > 0 and len(signals) % 5 == 0:
                        yield SSEEvent(
                            event="tool_status",
                            data={"status": "scanning", "message": f"Found {len(signals)} signals so far..."}
                        )
                    
                    # Stop if we have enough
                    if len(signals) >= max_results:
                        break
                        
                except Exception as e:
                    logger.warning(f"Error scanning {ticker}: {str(e)}")
                    continue
            
            # Sort by confidence
            signals.sort(key=lambda x: x["confidence"], reverse=True)
            
            yield {
                "success": True,
                "strategy_name": strategy.name,
                "tickers_scanned": len(tickers),
                "signals_found": len(signals),
                "signals": signals[:max_results],
                "message": f"✓ Found {len(signals)} trading signals from {len(tickers)} tickers"
            }
        
    except Exception as e:
        logger.error(f"Error scanning with strategy: {str(e)}", exc_info=True)
        yield {
            "success": False,
            "error": f"Failed to scan: {str(e)}",
            "message": f"Error: {str(e)}"
        }


@tool(
    name="list_strategies",
    description="Get all trading strategies created by the user",
    category="strategy"
)
def list_strategies(
    *,
    context: AgentContext,
    active_only: bool = True
):
    """List user's strategies"""
    from crud.strategy_v2 import get_user_strategies
    from database import SessionLocal
    
    try:
        with SessionLocal() as db:
            strategies = get_user_strategies(db, context.user_id, active_only)
            
            if not strategies:
                return {
                    "success": True,
                    "strategies": [],
                    "count": 0,
                    "message": "No strategies found. Create one with create_trading_strategy!"
                }
            
            strategy_list = [
                {
                    "strategy_id": s.id,
                    "name": s.name,
                    "description": s.description,
                    "num_rules": len(s.rules),
                    "created_at": s.created_at.isoformat(),
                    "is_active": s.is_active
                }
                for s in strategies
            ]
            
            return {
                "success": True,
                "strategies": strategy_list,
                "count": len(strategy_list),
                "message": f"Found {len(strategy_list)} strategies"
            }
    
    except Exception as e:
        logger.error(f"Error listing strategies: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": f"Failed to list strategies: {str(e)}"
        }


@tool(
    name="get_strategy_details",
    description="Get full details of a strategy including all rules",
    category="strategy"
)
def get_strategy_details(
    *,
    context: AgentContext,
    strategy_id: str
):
    """Get strategy details"""
    from crud.strategy_v2 import get_strategy
    from database import SessionLocal
    
    try:
        with SessionLocal() as db:
            strategy = get_strategy(db, strategy_id)
            
            if not strategy:
                return {
                    "success": False,
                    "error": f"Strategy {strategy_id} not found"
                }
            
            if strategy.user_id != context.user_id:
                return {
                    "success": False,
                    "error": "You don't have permission to access this strategy"
                }
            
            return {
                "success": True,
                "strategy": {
                    "id": strategy.id,
                    "name": strategy.name,
                    "description": strategy.description,
                    "rules": [
                        {
                            "order": rule.order,
                            "description": rule.description,
                            "decision_logic": rule.decision_logic,
                            "weight": rule.weight,
                            "data_sources": [ds.model_dump() for ds in rule.data_sources]
                        }
                        for rule in strategy.rules
                    ],
                    "risk_parameters": strategy.risk_parameters.model_dump(),
                    "stock_universe": strategy.stock_universe,
                    "created_at": strategy.created_at.isoformat(),
                    "is_active": strategy.is_active
                }
            }
    
    except Exception as e:
        logger.error(f"Error getting strategy details: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": f"Failed to get strategy: {str(e)}"
        }


@tool(
    name="delete_strategy",
    description="Delete a trading strategy",
    category="strategy"
)
def delete_strategy_v2(
    *,
    context: AgentContext,
    strategy_id: str
):
    """Delete a strategy"""
    from crud.strategy_v2 import get_strategy, delete_strategy
    from database import SessionLocal
    
    try:
        with SessionLocal() as db:
            strategy = get_strategy(db, strategy_id)
            
            if not strategy:
                return {
                    "success": False,
                    "error": f"Strategy {strategy_id} not found"
                }
            
            if strategy.user_id != context.user_id:
                return {
                    "success": False,
                    "error": "You don't have permission to delete this strategy"
                }
            
            success = delete_strategy(db, strategy_id)
            
            if success:
                return {
                    "success": True,
                    "strategy_id": strategy_id,
                    "message": f"✓ Strategy '{strategy.name}' deleted successfully"
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to delete strategy"
                }
    
    except Exception as e:
        logger.error(f"Error deleting strategy: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": f"Failed to delete strategy: {str(e)}"
        }

