"""
V2 Strategy Tools - Clean & Composable

Screening rules: BUY/SKIP decisions on candidates
Management rules: BUY/HOLD/SELL decisions on positions
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
    type: str
    endpoint: str
    parameters: Dict[str, Any] = Field(default_factory=dict)


class StrategyRuleInput(BaseModel):
    order: int
    description: str
    data_sources: List[DataSourceInput] = Field(default_factory=list)
    decision_logic: str
    weight: float = Field(1.0, ge=0, le=1)


class CandidateSourceInput(BaseModel):
    type: str = "universe"
    universe: Optional[str] = "sp500"
    tickers: Optional[List[str]] = None
    limit: Optional[int] = 50


class RiskParametersInput(BaseModel):
    position_size_pct: float = Field(20.0, gt=0, le=100)
    max_positions: int = Field(5, gt=0)
    stop_loss_pct: Optional[float] = Field(10.0, gt=0)
    take_profit_pct: Optional[float] = Field(25.0, gt=0)
    max_hold_days: Optional[int] = None


class CreateStrategyV2Params(BaseModel):
    name: str
    description: str
    candidate_source: CandidateSourceInput = Field(default_factory=CandidateSourceInput)
    screening_rules: List[StrategyRuleInput]
    management_rules: List[StrategyRuleInput] = Field(default_factory=list)
    risk_parameters: RiskParametersInput = Field(default_factory=RiskParametersInput)


# Tools

@tool(
    name="create_trading_strategy",
    description="""Create a rule-based trading strategy with $1000 budget.

**IMPORTANT: Use get_fmp_data BEFORE creating strategies to:**
- Research realistic thresholds (check actual P/E ratios, growth rates, etc.)
- Validate concepts with real market data
- Identify which FMP endpoints to use in data_sources

Screening rules: Evaluate candidates → BUY or SKIP
Management rules: Evaluate positions → BUY/HOLD/SELL

Candidate source options:
- {"type": "universe", "universe": "sp500"}  (or nasdaq100, dow30)
- {"type": "custom", "tickers": ["AAPL", "MSFT", "NVDA"]}
- {"type": "reddit_trending", "limit": 50}

**Best Practice Workflow:**
1. User describes strategy idea
2. Call get_fmp_data to research (e.g., check typical P/E ranges, revenue growth rates)
3. Design rules with specific thresholds based on data
4. Call create_trading_strategy with FMP endpoints in data_sources

Example:
{
    "name": "Tech Growth",
    "description": "Buy growing tech stocks",
    "candidate_source": {"type": "universe", "universe": "sp500"},
    "screening_rules": [
        {
            "order": 1,
            "description": "Filter tech stocks",
            "decision_logic": "If sector != Technology, SKIP",
            "weight": 0.3
        },
        {
            "order": 2,
            "description": "Check growth",
            "data_sources": [{"type": "fmp", "endpoint": "income-statement", "parameters": {"period": "annual", "limit": 2}}],
            "decision_logic": "If revenue growth >20%, BULLISH. Aggregate: if BULLISH, BUY else SKIP",
            "weight": 0.7
        }
    ],
    "management_rules": [
        {
            "order": 1,
            "description": "Exit rules",
            "decision_logic": "If P&L >= 25%, SELL (profit). If P&L <= -10%, SELL (loss). Otherwise HOLD",
            "weight": 1.0
        }
    ]
}

Use FMP endpoints like: income-statement, balance-sheet, key-metrics, financial-ratios, financial-growth, insider-trading, etc.""",
    category="strategy"
)
async def create_trading_strategy_v2(
    *,
    context: AgentContext,
    params: CreateStrategyV2Params
):
    """Create a rule-based trading strategy"""
    from models.strategy_v2 import TradingStrategyV2, StrategyRule, DataSource, CandidateSource, RiskParameters, StrategyBudget
    from crud.strategy_v2 import create_strategy, create_budget
    from database import SessionLocal
    import uuid
    
    yield SSEEvent(event="tool_status", data={"status": "creating", "message": f"Creating '{params.name}'..."})
    
    try:
        strategy_id = str(uuid.uuid4())
        
        strategy = TradingStrategyV2(
            id=strategy_id,
            user_id=context.user_id,
            name=params.name,
            description=params.description,
            candidate_source=CandidateSource(**params.candidate_source.model_dump()),
            screening_rules=[
                StrategyRule(
                    order=r.order,
                    description=r.description,
                    data_sources=[DataSource(**ds.model_dump()) for ds in r.data_sources],
                    decision_logic=r.decision_logic,
                    weight=r.weight
                )
                for r in params.screening_rules
            ],
            management_rules=[
                StrategyRule(
                    order=r.order,
                    description=r.description,
                    data_sources=[DataSource(**ds.model_dump()) for ds in r.data_sources],
                    decision_logic=r.decision_logic,
                    weight=r.weight
                )
                for r in params.management_rules
            ],
            risk_parameters=RiskParameters(**params.risk_parameters.model_dump())
        )
        
        budget = StrategyBudget(
            strategy_id=strategy_id,
            user_id=context.user_id,
            total_budget=1000.0,
            cash_available=1000.0
        )
        
        with SessionLocal() as db:
            create_strategy(db, strategy)
            create_budget(db, budget)
        
        yield {
            "success": True,
            "strategy_id": strategy.id,
            "name": strategy.name,
            "screening_rules": len(strategy.screening_rules),
            "management_rules": len(strategy.management_rules),
            "budget": 1000.0,
            "message": f"✓ '{params.name}' created with $1000 budget!"
        }
        
    except Exception as e:
        logger.error(f"Error creating strategy: {str(e)}", exc_info=True)
        yield {"success": False, "error": str(e)}


@tool(
    name="execute_strategy",
    description="""Run strategy: screen candidates AND manage positions.

Returns BUY/SELL/HOLD signals with full reasoning.""",
    category="strategy"
)
async def execute_strategy(
    *,
    context: AgentContext,
    strategy_id: str,
    limit_candidates: Optional[int] = None
):
    """Execute strategy"""
    from crud.strategy_v2 import get_strategy, get_budget, get_positions
    from services.strategy_executor import StrategyExecutor
    from modules.tools.clients.fmp import get_candidates_from_source
    from database import SessionLocal
    
    # Debug logging for limit_candidates parameter
    logger.info(f"execute_strategy called with limit_candidates={limit_candidates} (type: {type(limit_candidates)})")
    
    yield SSEEvent(event="tool_status", data={"status": "running", "message": "Executing strategy..."})
    
    try:
        with SessionLocal() as db:
            strategy = get_strategy(db, strategy_id)
            if not strategy or strategy.user_id != context.user_id:
                yield {"success": False, "error": "Strategy not found"}
                return
            
            budget = get_budget(db, strategy_id)
            positions = get_positions(db, strategy_id, open_only=True)
            
            executor = StrategyExecutor()
            decisions = []
            
            # 1. Manage existing positions
            if positions:
                yield SSEEvent(event="tool_status", data={
                    "status": "running", 
                    "message": f"Managing {len(positions)} existing positions..."
                })
                try:
                    position_decisions = await executor.manage_positions_parallel(strategy, positions)
                    decisions.extend([d.model_dump() for d in position_decisions])
                    yield SSEEvent(event="tool_status", data={
                        "status": "running",
                        "message": f"✓ Managed {len(position_decisions)} positions"
                    })
                except Exception as e:
                    logger.error(f"Error managing positions: {str(e)}", exc_info=True)
                    yield SSEEvent(event="tool_status", data={
                        "status": "error",
                        "message": f"Error managing positions: {str(e)}"
                    })
            
            # 2. Screen candidates (if room for more positions)
            if len(positions) < strategy.risk_parameters.max_positions and budget.cash_available > 0:
                try:
                    candidates = await get_candidates_from_source(strategy.candidate_source.model_dump())
                    # Apply candidate limit if specified
                    if limit_candidates is not None:
                        try:
                            limit = int(limit_candidates) if not isinstance(limit_candidates, int) else limit_candidates
                            candidates = candidates[:limit]
                        except (ValueError, TypeError) as e:
                            logger.warning(f"Invalid limit_candidates value: {limit_candidates} (type: {type(limit_candidates)}), ignoring limit")

                    
                    # Filter out tickers we already own
                    candidates_to_screen = [
                        ticker for ticker in candidates 
                        if not any(p.ticker == ticker for p in positions)
                    ]
                    
                    if candidates_to_screen:
                        yield SSEEvent(event="tool_status", data={
                            "status": "running",
                            "message": f"Screening {len(candidates_to_screen)} candidates (max 3 concurrent)..."
                        })
                        candidate_decisions = await executor.screen_candidates_parallel(strategy, candidates_to_screen)
                        # Only add BUY decisions
                        buy_decisions = [d for d in candidate_decisions if d.action == "BUY"]
                        decisions.extend([d.model_dump() for d in buy_decisions])
                        yield SSEEvent(event="tool_status", data={
                            "status": "running",
                            "message": f"✓ Found {len(buy_decisions)} BUY signals from {len(candidate_decisions)} screened"
                        })
                except Exception as e:
                    logger.error(f"Error screening candidates: {str(e)}", exc_info=True)
                    yield SSEEvent(event="tool_status", data={
                        "status": "error",
                        "message": f"Error screening candidates: {str(e)}"
                    })
            
            buy_sigs = [d for d in decisions if d['action'] == 'BUY']
            sell_sigs = [d for d in decisions if d['action'] == 'SELL']
            hold_sigs = [d for d in decisions if d['action'] == 'HOLD']
            
            yield {
                "success": True,
                "strategy_name": strategy.name,
                "decisions": decisions,
                "summary": {
                    "buy_signals": len(buy_sigs),
                    "sell_signals": len(sell_sigs),
                    "hold_signals": len(hold_sigs),
                    "positions": len(positions),
                    "cash": budget.cash_available
                },
                "message": f"✓ {len(buy_sigs)} BUY, {len(sell_sigs)} SELL, {len(hold_sigs)} HOLD"
            }
            
    except Exception as e:
        logger.error(f"Error executing strategy: {str(e)}", exc_info=True)
        yield {"success": False, "error": str(e)}


@tool(
    name="list_strategies",
    description="List all strategies",
    category="strategy"
)
def list_strategies(*, context: AgentContext, active_only: bool = True):
    """List strategies"""
    from crud.strategy_v2 import get_user_strategies
    from database import SessionLocal
    
    try:
        with SessionLocal() as db:
            strategies = get_user_strategies(db, context.user_id, active_only)
            return {
                "success": True,
                "strategies": [
                    {
                        "id": s.id,
                        "name": s.name,
                        "description": s.description,
                        "screening_rules": len(s.screening_rules),
                        "management_rules": len(s.management_rules)
                    }
                    for s in strategies
                ],
                "count": len(strategies)
            }
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e)}


@tool(
    name="get_strategy_details",
    description="Get strategy details",
    category="strategy"
)
def get_strategy_details(*, context: AgentContext, strategy_id: str):
    """Get details"""
    from crud.strategy_v2 import get_strategy, get_budget, get_positions
    from database import SessionLocal
    
    try:
        with SessionLocal() as db:
            strategy = get_strategy(db, strategy_id)
            if not strategy or strategy.user_id != context.user_id:
                return {"success": False, "error": "Not found"}
            
            budget = get_budget(db, strategy_id)
            positions = get_positions(db, strategy_id, open_only=True)
            
            return {
                "success": True,
                "strategy": strategy.model_dump(),
                "budget": budget.model_dump() if budget else {"total_budget": 1000, "cash_available": 1000},
                "positions": [p.model_dump() for p in positions]
            }
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e)}


@tool(
    name="delete_strategy",
    description="Delete strategy",
    category="strategy"
)
def delete_strategy_v2(*, context: AgentContext, strategy_id: str):
    """Delete"""
    from crud.strategy_v2 import get_strategy, delete_strategy
    from database import SessionLocal
    
    try:
        with SessionLocal() as db:
            strategy = get_strategy(db, strategy_id)
            if not strategy or strategy.user_id != context.user_id:
                return {"success": False, "error": "Not found"}
            
            delete_strategy(db, strategy_id)
            return {"success": True, "message": f"Deleted '{strategy.name}'"}
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e)}
