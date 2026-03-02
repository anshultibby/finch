"""
Pydantic models for Strategies
"""
from typing import Optional, List, Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field


# ============================================================================
# Config sub-models (what goes in Strategy.config JSONB)
# ============================================================================

class CapitalConfig(BaseModel):
    """Capital allocation config stored in Strategy.config"""
    total: float = Field(..., description="Total USD allocated to strategy")
    per_trade: float = Field(..., description="USD to risk per single trade")
    max_positions: int = Field(default=5, description="Maximum concurrent positions")

    class Config:
        extra = "allow"


class RiskLimits(BaseModel):
    """Risk limits for strategy execution"""
    max_order_usd: Optional[float] = Field(None, description="Maximum USD per single order")
    max_daily_usd: Optional[float] = Field(None, description="Maximum USD spend per day")
    allowed_services: List[str] = Field(
        default_factory=lambda: ["kalshi"],
        description="Which services this strategy can use",
    )

    class Config:
        extra = "allow"


class StrategyConfig(BaseModel):
    """Configuration stored in Strategy.config JSONB"""
    platform: Literal["kalshi", "alpaca"] = Field(..., description="Trading platform")
    description: str = Field(..., description="Plain language description of what strategy does")
    thesis: str = Field(default="", description="Why this strategy will make money")
    source_chat_id: Optional[str] = Field(None, description="Chat ID where strategy was created (UI linkback only)")
    schedule: Optional[str] = Field(None, description="Cron expression for scheduled runs")
    schedule_description: Optional[str] = Field(None, description="Human-readable schedule description")
    capital: Optional[CapitalConfig] = Field(None, description="Capital allocation config")
    risk_limits: Optional[RiskLimits] = Field(None, description="Risk limits for execution")
    approved_at: Optional[datetime] = Field(None, description="When strategy was approved")

    class Config:
        extra = "allow"


class StrategyStats(BaseModel):
    """Stats stored in Strategy.stats JSONB"""
    total_runs: int = Field(default=0)
    successful_runs: int = Field(default=0)
    failed_runs: int = Field(default=0)
    last_run_at: Optional[datetime] = None
    last_run_status: Optional[str] = None  # 'success', 'failed'
    last_run_summary: Optional[str] = None
    total_spent_usd: float = Field(default=0.0)
    total_profit_usd: float = Field(default=0.0)

    class Config:
        extra = "allow"


# ============================================================================
# Execution data model (what goes in StrategyExecution.data JSONB)
# ============================================================================

class ExecutionAction(BaseModel):
    """A single action taken during strategy execution"""
    type: str  # 'kalshi_order', 'alpaca_order', 'alert', etc.
    timestamp: datetime
    dry_run: bool = False
    details: dict = Field(default_factory=dict)

    class Config:
        extra = "allow"


class ExecutionData(BaseModel):
    """Data stored in StrategyExecution.data JSONB"""
    trigger: str  # 'scheduled', 'manual', 'dry_run'
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    logs: List[str] = Field(default_factory=list)
    summary: Optional[str] = None
    actions: List[ExecutionAction] = Field(default_factory=list)

    class Config:
        extra = "allow"


# ============================================================================
# API Request/Response models
# ============================================================================

class CreateStrategyRequest(BaseModel):
    """Request to create a new strategy"""
    name: str
    description: str
    platform: Literal["kalshi", "alpaca"]
    thesis: str = ""
    schedule: Optional[str] = None
    schedule_description: Optional[str] = None
    capital: Optional[CapitalConfig] = None
    risk_limits: Optional[RiskLimits] = None
    source_chat_id: Optional[str] = None
    # files: dict[filename -> content], written to strategy_files table by crud
    files: dict = Field(default_factory=dict, description="filename -> content")


class UpdateStrategyRequest(BaseModel):
    """Request to update a strategy"""
    name: Optional[str] = None
    enabled: Optional[bool] = None
    schedule: Optional[str] = None
    schedule_description: Optional[str] = None
    risk_limits: Optional[RiskLimits] = None
    description: Optional[str] = None
    # Updating code files: filename -> new content (empty dict means no change)
    files: Optional[dict] = None


class StrategyResponse(BaseModel):
    """Strategy response for API (user-facing)"""
    id: str
    name: str
    description: str
    platform: str
    enabled: bool
    approved: bool
    schedule_description: Optional[str] = None

    # Stats
    total_runs: int = 0
    successful_runs: int = 0
    last_run_at: Optional[datetime] = None
    last_run_status: Optional[str] = None
    last_run_summary: Optional[str] = None

    # Timestamps
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StrategyDetailResponse(StrategyResponse):
    """Detailed strategy response — includes config and file list"""
    thesis: str = ""
    source_chat_id: Optional[str] = None
    schedule: Optional[str] = None
    risk_limits: Optional[RiskLimits] = None
    capital: Optional[CapitalConfig] = None
    stats: StrategyStats = Field(default_factory=StrategyStats)
    # files: list of {filename, content} — populated by route
    files: List[dict] = Field(default_factory=list)


class ExecutionResponse(BaseModel):
    """Strategy execution response"""
    id: str
    strategy_id: str
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
    """Detailed execution response with full data"""
    duration_ms: Optional[int] = None
    logs: List[str] = []
    actions: List[ExecutionAction] = []
    result: Optional[Any] = None


class RunStrategyRequest(BaseModel):
    """Request to manually run a strategy"""
    dry_run: bool = Field(default=True, description="If true, simulate without real orders")


class RunStrategyResponse(BaseModel):
    """Response from running a strategy"""
    execution_id: str
    status: str
    summary: Optional[str] = None
    actions: List[ExecutionAction] = []
    error: Optional[str] = None


# ============================================================================
# LLM Tool models
# ============================================================================

class StrategyInfoForLLM(BaseModel):
    """Strategy info formatted for LLM context"""
    id: str
    name: str
    description: str
    platform: str
    status: str  # 'active', 'paused', 'needs_approval', 'never_run'
    schedule: Optional[str] = None
    last_run: Optional[str] = None

    @classmethod
    def from_strategy(cls, strategy) -> "StrategyInfoForLLM":
        config = strategy.config or {}
        stats = strategy.stats or {}

        if not strategy.approved:
            status = "needs_approval"
        elif not strategy.enabled:
            status = "paused"
        elif stats.get("total_runs", 0) == 0:
            status = "never_run"
        else:
            status = "active"

        last_run = None
        if stats.get("last_run_at"):
            last_run = f"{stats.get('last_run_status', 'unknown')}: {stats.get('last_run_summary', 'No summary')}"

        return cls(
            id=strategy.id,
            name=strategy.name,
            description=config.get("description", ""),
            platform=config.get("platform", ""),
            status=status,
            schedule=config.get("schedule_description"),
            last_run=last_run,
        )
