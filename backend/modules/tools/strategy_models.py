"""
Pydantic models for strategy tool parameters

These models define the input/output schemas for strategy management tools,
making the code cleaner and providing automatic validation.
"""
from pydantic import BaseModel, Field
from typing import Optional, Literal, Any
from datetime import date


class StrategyConditionParam(BaseModel):
    """A single entry or exit condition"""
    field: str = Field(description="Field name (e.g., 'rsi', 'insider_buy_amount', 'price_change_pct')")
    operator: Literal["gt", "lt", "gte", "lte", "eq", "between", "in"] = Field(description="Comparison operator")
    value: Any = Field(description="Value to compare against (number, list, etc.)")
    description: str = Field(description="Plain English explanation of this condition")


class DataRequirementParam(BaseModel):
    """Data needed for the strategy"""
    source: Literal["fmp", "reddit", "calculated", "user_portfolio"] = Field(description="Data source")
    data_type: str = Field(description="Type of data (e.g., 'insider_trading', 'price_history', 'rsi')")
    parameters: dict = Field(default_factory=dict, description="Additional parameters for this data source")


class RiskParametersParam(BaseModel):
    """Risk management settings"""
    stop_loss_pct: Optional[float] = Field(None, description="Stop loss percentage")
    take_profit_pct: Optional[float] = Field(None, description="Take profit target percentage")
    max_hold_days: Optional[int] = Field(None, description="Maximum days to hold position")
    position_size_pct: float = Field(5.0, description="Position size as % of portfolio")
    max_positions: int = Field(5, description="Maximum concurrent positions")


class CreateStrategyParams(BaseModel):
    """Parameters for creating a new trading strategy - fully structured by the main agent"""
    name: str = Field(description="Short, descriptive name for the strategy")
    description: str = Field(description="Detailed explanation of the strategy")
    timeframe: Literal["short_term", "medium_term", "long_term"] = Field(
        description="Strategy timeframe: short_term (1-4 weeks), medium_term (1-3 months), long_term (3+ months)"
    )
    data_requirements: list[DataRequirementParam] = Field(
        description="List of data sources needed for this strategy"
    )
    entry_conditions: list[StrategyConditionParam] = Field(
        description="Conditions that must be met to enter a trade"
    )
    entry_logic: Literal["AND", "OR"] = Field(
        default="AND",
        description="How to combine entry conditions (all must be true = AND, any can be true = OR)"
    )
    exit_conditions: list[StrategyConditionParam] = Field(
        description="Conditions for exiting a trade"
    )
    exit_logic: Literal["AND", "OR"] = Field(
        default="OR",
        description="How to combine exit conditions"
    )
    risk_parameters: RiskParametersParam = Field(
        description="Risk management settings"
    )


class BacktestStrategyParams(BaseModel):
    """Parameters for backtesting a strategy"""
    strategy_id: str = Field(
        description="ID of the strategy to backtest"
    )
    start_date: Optional[str] = Field(
        None,
        description="Start date for backtest in YYYY-MM-DD format (defaults to 2 years ago)"
    )
    end_date: Optional[str] = Field(
        None,
        description="End date for backtest in YYYY-MM-DD format (defaults to today)"
    )
    initial_capital: float = Field(
        100000,
        description="Starting capital for backtest (default $100,000)"
    )


class GetStrategyDetailsParams(BaseModel):
    """Parameters for getting strategy details"""
    strategy_id: str = Field(
        description="The ID of the strategy to retrieve"
    )


class ListStrategiesParams(BaseModel):
    """Parameters for listing user strategies"""
    active_only: bool = Field(
        True,
        description="If true, only return active strategies (default True)"
    )


class UpdateStrategyParams(BaseModel):
    """Parameters for updating a strategy"""
    strategy_id: str = Field(
        description="The ID of the strategy to update"
    )
    name: Optional[str] = Field(
        None,
        description="New name for the strategy"
    )
    description: Optional[str] = Field(
        None,
        description="New description for the strategy"
    )
    is_active: Optional[bool] = Field(
        None,
        description="Set active status (true to activate, false to pause)"
    )


class DeleteStrategyParams(BaseModel):
    """Parameters for deleting a strategy"""
    strategy_id: str = Field(
        description="The ID of the strategy to delete"
    )


# ============================================================================
# Response Models
# ============================================================================

class ConditionInfo(BaseModel):
    """Information about an entry/exit condition"""
    field: str
    operator: str
    value: Any  # Can be float, int, list, etc.
    description: Optional[str] = None


class RiskParametersInfo(BaseModel):
    """Risk management parameters"""
    stop_loss_pct: Optional[float] = None
    take_profit_pct: Optional[float] = None
    max_hold_days: Optional[int] = None
    position_size_pct: float = 5.0
    max_positions: int = 5


class DataRequirementInfo(BaseModel):
    """Data requirement for a strategy"""
    source: Literal["fmp", "reddit", "calculated", "user_portfolio"]
    data_type: str
    parameters: dict = {}


class StrategyInfo(BaseModel):
    """Summary information about a strategy"""
    strategy_id: str
    name: str
    description: str
    timeframe: Literal["short_term", "medium_term", "long_term"]
    is_active: bool
    created_at: str


class StrategyPerformanceInfo(BaseModel):
    """Performance metrics for a strategy"""
    signals_generated: int = 0
    signals_acted_on: int = 0
    actual_trades: int = 0
    actual_wins: int = 0
    actual_return_pct: float = 0.0
    last_signal_date: Optional[str] = None


class BacktestInfo(BaseModel):
    """Backtest results summary"""
    backtest_id: str
    start_date: str
    end_date: str
    total_trades: int
    win_rate: float
    total_return_pct: float
    profit_factor: float
    max_drawdown_pct: float


class StrategyComparisonInfo(BaseModel):
    """Strategy comparison data"""
    strategy_name: str
    timeframe: str
    signals_generated: int
    win_rate: Optional[float] = None
    actual_return_pct: float
    hypothetical_return_pct: float
    last_signal: Optional[str] = None
    is_active: bool


class StrategyDetailsResponse(BaseModel):
    """Complete strategy details response"""
    success: bool
    strategy: Optional[dict] = None
    performance: Optional[StrategyPerformanceInfo] = None
    latest_backtest: Optional[BacktestInfo] = None
    error: Optional[str] = None


class CompareStrategiesResponse(BaseModel):
    """Response for strategy comparison"""
    success: bool
    strategies: list[StrategyComparisonInfo] = []
    count: int = 0
    message: str
    error: Optional[str] = None


class ListStrategiesResponse(BaseModel):
    """Response for listing strategies"""
    success: bool
    strategies: list[StrategyInfo] = []
    count: int = 0
    message: str
    error: Optional[str] = None


class CreateStrategyResponse(BaseModel):
    """Response for creating a strategy"""
    success: bool
    strategy_id: Optional[str] = None
    strategy_name: Optional[str] = None
    description: Optional[str] = None
    timeframe: Optional[str] = None
    entry_conditions: list[ConditionInfo] = []
    exit_conditions: list[ConditionInfo] = []
    risk_parameters: Optional[RiskParametersInfo] = None
    message: Optional[str] = None
    error: Optional[str] = None
    issues: Optional[list[str]] = None


class UpdateStrategyResponse(BaseModel):
    """Response for updating a strategy"""
    success: bool
    strategy_id: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    message: Optional[str] = None
    error: Optional[str] = None


class DeleteStrategyResponse(BaseModel):
    """Response for deleting a strategy"""
    success: bool
    strategy_id: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None


class RefineStrategyParams(BaseModel):
    """Parameters for refining an existing strategy - includes full updated structure"""
    strategy_id: str = Field(
        description="The ID of the strategy to update"
    )
    # Include all fields from CreateStrategyParams
    name: str = Field(description="Updated name for the strategy")
    description: str = Field(description="Updated description")
    timeframe: Literal["short_term", "medium_term", "long_term"]
    data_requirements: list[DataRequirementParam]
    entry_conditions: list[StrategyConditionParam]
    entry_logic: Literal["AND", "OR"] = "AND"
    exit_conditions: list[StrategyConditionParam]
    exit_logic: Literal["AND", "OR"] = "OR"
    risk_parameters: RiskParametersParam

