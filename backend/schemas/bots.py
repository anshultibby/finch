"""
Pydantic models for Trading Bots
"""
from typing import Optional, List, Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field


# ============================================================================
# Config sub-models (stored in TradingBot.config JSONB)
# ============================================================================

class CapitalConfig(BaseModel):
    amount_usd: Optional[float] = Field(None, description="Per-position budget (USD)")
    max_positions: Optional[int] = Field(None, description="Maximum concurrent positions")
    balance_usd: Optional[float] = Field(None, description="Running capital balance (auto-tracked)")

    class Config:
        extra = "allow"


class RiskLimits(BaseModel):
    max_order_usd: Optional[float] = Field(None, description="Maximum USD per single order")
    max_daily_usd: Optional[float] = Field(None, description="Maximum USD spend per day")
    allowed_services: List[str] = Field(
        default_factory=lambda: ["kalshi"],
        description="Which services this bot can use",
    )

    class Config:
        extra = "allow"


class ExitConfig(BaseModel):
    type: Literal["event_resolution", "time_based", "profit_target", "stop_loss", "indefinite", "composite"] = "indefinite"
    hold_days: Optional[int] = None
    profit_target_pct: Optional[float] = None
    stop_loss_pct: Optional[float] = None
    resolve_on_event: bool = True

    class Config:
        extra = "allow"


class BotConfig(BaseModel):
    """Configuration stored in TradingBot.config JSONB"""
    platform: Literal["kalshi", "alpaca"] = Field(default="kalshi", description="Trading platform")
    mandate: str = Field(default="", description="Bot's trading mandate / instructions")
    schedule: Optional[str] = Field(None, description="Cron expression for scheduled ticks")
    schedule_description: Optional[str] = Field(None, description="Human-readable schedule description")
    capital: Optional[CapitalConfig] = Field(None, description="Capital allocation config")
    risk_limits: Optional[RiskLimits] = Field(None, description="Risk limits for execution")
    model: str = Field(default="claude-sonnet-4-20250514", description="LLM model for bot reasoning")
    approved_at: Optional[datetime] = Field(None, description="When bot was approved for live trading")
    paper_mode: bool = Field(default=True, description="If True, ticks use dry_run (no real orders)")

    class Config:
        extra = "allow"


class BotStats(BaseModel):
    """Stats stored in TradingBot.stats JSONB"""
    total_runs: int = Field(default=0)
    successful_runs: int = Field(default=0)
    failed_runs: int = Field(default=0)
    last_run_at: Optional[datetime] = None
    last_run_status: Optional[str] = None
    last_run_summary: Optional[str] = None
    total_spent_usd: float = Field(default=0.0)
    total_profit_usd: float = Field(default=0.0)
    open_unrealized_pnl: float = Field(default=0.0)
    paper_profit_usd: float = Field(default=0.0)
    paper_unrealized_pnl: float = Field(default=0.0)

    class Config:
        extra = "allow"


# ============================================================================
# Position response
# ============================================================================

class BotPositionResponse(BaseModel):
    id: str
    bot_id: str
    market: str
    platform: str
    side: str
    entry_price: float
    entry_time: datetime
    quantity: float
    cost_usd: float
    status: str
    exit_config: ExitConfig = Field(default_factory=ExitConfig)

    market_title: Optional[str] = None
    event_ticker: Optional[str] = None

    entered_via: Optional[str] = None
    closed_via: Optional[str] = None

    closed_at: Optional[datetime] = None
    exit_price: Optional[float] = None
    realized_pnl_usd: Optional[float] = None
    close_reason: Optional[str] = None

    current_price: Optional[float] = None
    unrealized_pnl_usd: Optional[float] = None
    last_priced_at: Optional[datetime] = None

    price_history: List[dict] = Field(default_factory=list)
    monitor_note: Optional[str] = None
    paper: bool = False

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Execution models
# ============================================================================

class ExecutionAction(BaseModel):
    type: str
    timestamp: datetime
    dry_run: bool = False
    details: dict = Field(default_factory=dict)

    class Config:
        extra = "allow"


class ExecutionResponse(BaseModel):
    id: str
    bot_id: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    trigger: str
    summary: Optional[str] = None
    error: Optional[str] = None
    actions_count: int = 0

    class Config:
        from_attributes = True


class ExecutionDetailResponse(ExecutionResponse):
    duration_ms: Optional[int] = None
    logs: List[str] = []
    actions: List[ExecutionAction] = []
    result: Optional[Any] = None


# ============================================================================
# API Request/Response models
# ============================================================================

class CreateBotRequest(BaseModel):
    name: str = Field(default="New Bot")
    platform: Literal["kalshi", "alpaca"] = "kalshi"
    icon: Optional[str] = None


class UpdateBotRequest(BaseModel):
    name: Optional[str] = None
    icon: Optional[str] = None
    enabled: Optional[bool] = None
    mandate: Optional[str] = None
    schedule: Optional[str] = None
    schedule_description: Optional[str] = None
    risk_limits: Optional[RiskLimits] = None
    capital: Optional[CapitalConfig] = None
    paper_mode: Optional[bool] = None
    model: Optional[str] = None


class BotResponse(BaseModel):
    """Bot response for list/card view"""
    id: str
    name: str
    icon: Optional[str] = None
    platform: str
    enabled: bool
    approved: bool
    schedule_description: Optional[str] = None

    # Stats
    total_runs: int = 0
    last_run_at: Optional[datetime] = None
    last_run_status: Optional[str] = None
    last_run_summary: Optional[str] = None

    # Positions
    open_positions_count: int = 0

    # P&L
    total_profit_usd: float = 0.0
    open_unrealized_pnl: float = 0.0

    # Capital
    capital_balance: Optional[float] = None

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BotDetailResponse(BotResponse):
    """Detailed bot response — includes config, files, positions"""
    mandate: str = ""
    schedule: Optional[str] = None
    risk_limits: Optional[RiskLimits] = None
    capital: Optional[CapitalConfig] = None
    paper_mode: bool = True
    model: str = "claude-sonnet-4-20250514"
    directory: Optional[str] = None
    stats: BotStats = Field(default_factory=BotStats)
    files: List[dict] = Field(default_factory=list)
    positions: List[BotPositionResponse] = Field(default_factory=list)
    closed_positions: List[BotPositionResponse] = Field(default_factory=list)


class RunBotRequest(BaseModel):
    dry_run: bool = Field(default=True, description="If true, simulate without real orders")


class RunBotResponse(BaseModel):
    execution_id: str
    status: str
    summary: Optional[str] = None
    actions: List[ExecutionAction] = []
    error: Optional[str] = None


# ============================================================================
# Trade Log models
# ============================================================================

class WakeupResponse(BaseModel):
    """A scheduled bot wakeup."""
    id: str
    bot_id: str
    trigger_at: datetime
    trigger_type: str
    reason: str
    context: dict = Field(default_factory=dict)
    status: str
    chat_id: Optional[str] = None
    triggered_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TradeLogResponse(BaseModel):
    """A single trade log entry — every buy/sell attempted by any bot."""
    id: str
    bot_id: str
    bot_name: Optional[str] = None
    bot_icon: Optional[str] = None
    execution_id: Optional[str] = None
    position_id: Optional[str] = None

    action: str           # "buy" or "sell"
    market: str
    market_title: Optional[str] = None
    platform: str
    side: Optional[str] = None
    price: Optional[float] = None
    quantity: Optional[int] = None
    cost_usd: Optional[float] = None

    status: str           # executed, dry_run, failed, pending_approval, approved, rejected, expired
    approval_method: Optional[str] = None
    approved_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    error: Optional[str] = None
    dry_run: bool = False

    created_at: datetime

    class Config:
        from_attributes = True
