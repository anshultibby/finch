"""
Strategy V2 Models - Clean & Composable

A strategy has:
- Candidates: Where to find stocks to screen
- Screening rules: Decide BUY/SKIP for candidates
- Management rules: Decide BUY/HOLD/SELL for positions
- Budget: Default $1000
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime, date
import uuid


class DataSource(BaseModel):
    """What data to fetch for a rule"""
    type: Literal["fmp", "reddit", "portfolio", "calculated"]
    endpoint: str
    parameters: Dict[str, Any] = Field(default_factory=dict)


class StrategyRule(BaseModel):
    """A single rule - simple and composable"""
    order: int = Field(..., description="Execution order")
    description: str = Field(..., description="What this rule checks")
    data_sources: List[DataSource] = Field(
        default_factory=list,
        description="Data needed for this rule"
    )
    decision_logic: str = Field(
        ...,
        description="Natural language: how to interpret the data and decide"
    )
    weight: float = Field(1.0, ge=0.0, le=1.0, description="Rule importance")


class CandidateSource(BaseModel):
    """Where to get stocks to screen"""
    type: Literal["universe", "reddit_trending", "custom", "sector", "tickers"] = "universe"
    
    # For "universe" type
    universe: Optional[str] = Field("sp500", description="sp500, nasdaq100, dow30")
    
    # For "custom" or "tickers" type (both mean the same thing)
    tickers: Optional[List[str]] = None
    
    # For "reddit_trending" type
    limit: Optional[int] = Field(50, description="Top N trending stocks")
    
    # For "sector" type (applies to universe)
    sector: Optional[str] = None  # "Technology", "Healthcare", etc.


class RiskParameters(BaseModel):
    """Risk management - simple defaults"""
    position_size_pct: float = Field(20.0, gt=0, le=100, description="% of budget per position")
    max_positions: int = Field(5, gt=0, description="Max concurrent positions")
    stop_loss_pct: Optional[float] = Field(10.0, gt=0, description="Auto-sell if loss >= this")
    take_profit_pct: Optional[float] = Field(25.0, gt=0, description="Auto-sell if profit >= this")
    max_hold_days: Optional[int] = Field(None, gt=0, description="Max days to hold")


class TradingStrategyV2(BaseModel):
    """Modern rule-based trading strategy"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    chat_id: str
    name: str
    description: str
    
    # WHERE to find stocks to screen
    candidate_source: CandidateSource = Field(
        default_factory=lambda: CandidateSource(type="universe", universe="sp500")
    )
    
    # HOW to screen candidates (BUY/SKIP)
    screening_rules: List[StrategyRule] = Field(
        ...,
        min_length=1,
        description="Rules to decide which candidates to BUY (or SKIP)"
    )
    
    # HOW to manage positions (BUY/HOLD/SELL)
    management_rules: List[StrategyRule] = Field(
        default_factory=list,
        description="Rules to decide what to do with positions we own"
    )
    
    # Risk management
    risk_parameters: RiskParameters = Field(default_factory=RiskParameters)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True


# ============================================================================
# Execution Results
# ============================================================================

class RuleDecisionResponse(BaseModel):
    """LLM response format for a single rule evaluation"""
    action: Literal["CONTINUE", "SKIP", "BUY", "SELL", "HOLD"]
    signal: Literal["BULLISH", "BEARISH", "NEUTRAL"]
    signal_value: float = Field(..., ge=0, le=1, description="0=bearish, 0.5=neutral, 1=bullish")
    reasoning: str = Field(..., description="Brief explanation of the decision")
    confidence: int = Field(..., ge=0, le=100, description="Confidence level 0-100")


class StrategyDecision(BaseModel):
    """Result of running rules on a ticker"""
    decision_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    strategy_id: str
    ticker: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Decision
    action: Literal["BUY", "SELL", "HOLD", "SKIP"]
    confidence: float = Field(..., ge=0, le=100)
    reasoning: str  # Step-by-step explanation
    
    # Details
    rule_results: List[Dict[str, Any]]
    data_snapshot: Dict[str, Any]
    current_price: float
    
    # If managing a position
    position_data: Optional[Dict[str, Any]] = None


# ============================================================================
# Position & Budget Tracking
# ============================================================================

class StrategyPosition(BaseModel):
    """Track what a strategy owns"""
    position_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    strategy_id: str
    user_id: str
    chat_id: str
    ticker: str
    
    # Entry
    shares: float
    entry_price: float
    entry_date: date
    entry_decision_id: str
    
    # Current state
    current_price: float = 0.0
    current_value: float = 0.0
    pnl: float = 0.0
    pnl_pct: float = 0.0
    days_held: int = 0
    
    # Exit
    exit_date: Optional[date] = None
    exit_price: Optional[float] = None
    exit_decision_id: Optional[str] = None
    is_open: bool = True
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class StrategyBudget(BaseModel):
    """Track strategy's money"""
    strategy_id: str
    user_id: str
    chat_id: str
    
    total_budget: float = Field(1000.0, description="Default $1000")
    cash_available: float
    position_value: float = 0.0
    
    @property
    def total_value(self) -> float:
        return self.cash_available + self.position_value
    
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class StrategyExecutionResult(BaseModel):
    """Results of running a strategy"""
    strategy_id: str
    strategy_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Decisions
    screening_decisions: List[StrategyDecision] = []  # From screening candidates
    management_decisions: List[StrategyDecision] = []  # From managing positions
    
    # State
    budget: StrategyBudget
    positions: List[StrategyPosition]
    
    # Summary
    @property
    def buy_signals(self) -> int:
        return sum(1 for d in self.screening_decisions + self.management_decisions if d.action == "BUY")
    
    @property
    def sell_signals(self) -> int:
        return sum(1 for d in self.management_decisions if d.action == "SELL")
    
    @property
    def hold_signals(self) -> int:
        return sum(1 for d in self.management_decisions if d.action == "HOLD")
