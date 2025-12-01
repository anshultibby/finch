"""
Modern LLM-Native Trading Strategy Models

Strategies are natural language rule scripts that an LLM executes to make decisions.
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime, date
import uuid


class DataSource(BaseModel):
    """Defines a data source for a rule"""
    type: Literal["fmp", "reddit", "portfolio", "calculated"]
    endpoint: str  # e.g., "income-statement", "ticker_sentiment", "rsi"
    parameters: Dict[str, Any] = Field(default_factory=dict)  # API parameters
    
    class Config:
        json_schema_extra = {
            "example": {
                "type": "fmp",
                "endpoint": "insider-trading",
                "parameters": {"days": 30}
            }
        }


class StrategyRule(BaseModel):
    """A single rule in a trading strategy"""
    order: int = Field(..., description="Execution order (1-based)")
    description: str = Field(..., description="Human-readable description of what this rule does")
    data_sources: List[DataSource] = Field(
        default_factory=list,
        description="Data sources to fetch before evaluating this rule"
    )
    decision_logic: str = Field(
        ...,
        description="Natural language description of how to interpret the data and make a decision"
    )
    weight: float = Field(
        1.0,
        ge=0.0,
        le=1.0,
        description="Importance of this rule in final decision (0-1)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "order": 1,
                "description": "Check insider buying activity",
                "data_sources": [
                    {
                        "type": "fmp",
                        "endpoint": "insider-trading",
                        "parameters": {"days": 30}
                    }
                ],
                "decision_logic": "If insiders bought more than $500k total in the last 30 days, this is a BULLISH signal. Otherwise neutral.",
                "weight": 0.3
            }
        }


class RiskParameters(BaseModel):
    """Risk management settings"""
    position_size_pct: float = Field(
        5.0,
        gt=0,
        le=100,
        description="Position size as % of portfolio"
    )
    max_positions: int = Field(
        5,
        gt=0,
        description="Maximum concurrent positions"
    )
    stop_loss_pct: Optional[float] = Field(
        None,
        gt=0,
        description="Stop loss percentage from entry"
    )
    take_profit_pct: Optional[float] = Field(
        None,
        gt=0,
        description="Take profit percentage from entry"
    )
    max_hold_days: Optional[int] = Field(
        None,
        gt=0,
        description="Maximum days to hold a position"
    )


class TradingStrategyV2(BaseModel):
    """Modern rule-based trading strategy"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    name: str = Field(..., description="Strategy name")
    description: str = Field(..., description="Overall strategy description")
    
    # Core strategy logic
    rules: List[StrategyRule] = Field(
        ...,
        min_length=1,
        description="List of rules that define the strategy"
    )
    
    # Risk management
    risk_parameters: RiskParameters
    
    # Target universe
    stock_universe: Optional[List[str]] = Field(
        None,
        description="List of tickers to scan. If None, use S&P 500"
    )
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True
    version: int = Field(2, description="Strategy model version")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user123",
                "name": "Tech Growth + Social Sentiment",
                "description": "Buy tech stocks with strong fundamentals and positive social buzz",
                "rules": [
                    {
                        "order": 1,
                        "description": "Verify it's a technology stock",
                        "data_sources": [
                            {
                                "type": "fmp",
                                "endpoint": "company-profile",
                                "parameters": {}
                            }
                        ],
                        "decision_logic": "Check if sector is 'Technology'. If not, SKIP this stock entirely.",
                        "weight": 0.2
                    },
                    {
                        "order": 2,
                        "description": "Check revenue growth",
                        "data_sources": [
                            {
                                "type": "fmp",
                                "endpoint": "income-statement",
                                "parameters": {"period": "annual", "limit": 2}
                            }
                        ],
                        "decision_logic": "If YoY revenue growth is >20%, this is BULLISH. If <0%, BEARISH. Otherwise neutral.",
                        "weight": 0.3
                    },
                    {
                        "order": 3,
                        "description": "Check social sentiment on Reddit",
                        "data_sources": [
                            {
                                "type": "reddit",
                                "endpoint": "ticker_sentiment",
                                "parameters": {"days": 7}
                            }
                        ],
                        "decision_logic": "If sentiment score >0.7 and mentions increasing, BULLISH. If <0.3, BEARISH.",
                        "weight": 0.3
                    },
                    {
                        "order": 4,
                        "description": "Make final decision",
                        "data_sources": [],
                        "decision_logic": "Aggregate all signals. If weighted average is >0.6, BUY. If <0.4, SKIP. Provide confidence score.",
                        "weight": 0.2
                    }
                ],
                "risk_parameters": {
                    "position_size_pct": 5.0,
                    "max_positions": 5,
                    "stop_loss_pct": 12.0,
                    "take_profit_pct": 25.0,
                    "max_hold_days": 90
                }
            }
        }


class StrategyDecision(BaseModel):
    """Result of executing a strategy on a ticker"""
    decision_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    strategy_id: str
    ticker: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Final decision
    action: Literal["BUY", "SELL", "HOLD", "SKIP"]
    confidence: float = Field(..., ge=0, le=100, description="Confidence score 0-100")
    reasoning: str = Field(..., description="Step-by-step explanation of the decision")
    
    # Rule-by-rule breakdown
    rule_results: List[Dict[str, Any]] = Field(
        ...,
        description="Results from each rule execution"
    )
    
    # Data used
    data_snapshot: Dict[str, Any] = Field(
        ...,
        description="All data fetched and used for this decision"
    )
    
    # Price context
    current_price: float
    
    class Config:
        json_schema_extra = {
            "example": {
                "strategy_id": "strat-123",
                "ticker": "NVDA",
                "action": "BUY",
                "confidence": 87,
                "reasoning": """
Step 1 (Tech Stock Check): PASSED - NVDA is in Technology sector
Step 2 (Revenue Growth): BULLISH - 56% YoY revenue growth (target was >20%)
Step 3 (Social Sentiment): BULLISH - Reddit sentiment 0.82, mentions up 40% this week
Step 4 (Final Decision): BUY - Weighted score: 0.78 (threshold 0.6)

Confidence: 87% based on strong fundamentals and social momentum
                """.strip(),
                "rule_results": [
                    {
                        "rule_order": 1,
                        "description": "Verify it's a technology stock",
                        "result": "PASS",
                        "signal": "NEUTRAL"
                    },
                    {
                        "rule_order": 2,
                        "description": "Check revenue growth",
                        "result": "PASS",
                        "signal": "BULLISH",
                        "value": 0.56
                    },
                    {
                        "rule_order": 3,
                        "description": "Check social sentiment",
                        "result": "PASS",
                        "signal": "BULLISH",
                        "value": 0.82
                    },
                    {
                        "rule_order": 4,
                        "description": "Make final decision",
                        "result": "BUY",
                        "weighted_score": 0.78
                    }
                ],
                "data_snapshot": {
                    "company_profile": {"sector": "Technology"},
                    "income_statement": [
                        {"revenue": 26974000000, "date": "2023-01-29"},
                        {"revenue": 16675000000, "date": "2022-01-30"}
                    ],
                    "reddit_sentiment": {
                        "score": 0.82,
                        "mentions": 1453,
                        "trending": "up"
                    }
                },
                "current_price": 495.32
            }
        }


class ForwardTest(BaseModel):
    """Forward testing tracker for a strategy"""
    test_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    strategy_id: str
    user_id: str
    start_date: date = Field(default_factory=date.today)
    
    # Signals generated
    signals: List[StrategyDecision] = Field(default_factory=list)
    total_signals: int = 0
    buy_signals: int = 0
    sell_signals: int = 0
    
    # User interaction
    signals_acted_on: int = 0
    signals_ignored: int = 0
    
    # Performance tracking
    hypothetical_pnl: float = 0.0  # If user took all signals
    actual_pnl: float = 0.0  # Signals user actually acted on
    
    # Status
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class StrategyPerformanceMetrics(BaseModel):
    """Aggregate performance metrics for a strategy"""
    strategy_id: str
    strategy_name: str
    
    # Time period
    period_start: date
    period_end: date
    days_active: int
    
    # Signal statistics
    total_signals: int
    buy_signals: int
    sell_signals: int
    avg_confidence: float
    
    # Outcome (if user acted on signals)
    signals_acted_on: int
    win_rate: Optional[float] = None
    avg_return_pct: Optional[float] = None
    
    # Hypothetical performance (if took all signals)
    hypothetical_win_rate: Optional[float] = None
    hypothetical_return_pct: Optional[float] = None
    
    # Best signal
    best_signal: Optional[Dict[str, Any]] = None
    worst_signal: Optional[Dict[str, Any]] = None

