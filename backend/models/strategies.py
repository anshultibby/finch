"""
Pydantic models for Strategies

These models define the API interface and JSONB structure for strategies.
"""
from typing import Optional, List, Any
from datetime import datetime
from pydantic import BaseModel, Field


# ============================================================================
# Config sub-models (what goes in Strategy.config JSONB)
# ============================================================================

class RiskLimits(BaseModel):
    """Risk limits for strategy execution"""
    max_order_usd: Optional[float] = Field(None, description="Maximum USD per single order")
    max_daily_usd: Optional[float] = Field(None, description="Maximum USD spend per day")
    max_position_usd: Optional[float] = Field(None, description="Maximum USD in any single position")
    allowed_services: List[str] = Field(default_factory=lambda: ["kalshi"], description="Which services this strategy can use")
    
    class Config:
        extra = "allow"  # Allow additional risk limit fields


class StrategyConfig(BaseModel):
    """Configuration stored in Strategy.config JSONB"""
    description: str = Field(..., description="Plain language description of what strategy does")
    source_chat_id: Optional[str] = Field(None, description="Chat ID where strategy was created")
    file_ids: List[str] = Field(..., description="List of ChatFile IDs containing strategy code")
    entrypoint: str = Field(default="strategy.py", description="Which file to execute")
    schedule: Optional[str] = Field(None, description="Cron expression for scheduled runs")
    schedule_description: Optional[str] = Field(None, description="Human-readable schedule description")
    risk_limits: Optional[RiskLimits] = Field(None, description="Risk limits for execution")
    approved_at: Optional[datetime] = Field(None, description="When strategy was approved")
    
    class Config:
        extra = "allow"  # Allow additional config fields


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
        extra = "allow"  # Allow additional stat fields


# ============================================================================
# Execution data model (what goes in StrategyExecution.data JSONB)
# ============================================================================

class ExecutionAction(BaseModel):
    """A single action taken during strategy execution"""
    type: str  # 'kalshi_order', 'alpaca_order', 'alert', etc.
    timestamp: datetime
    dry_run: bool = False
    details: dict = Field(default_factory=dict)  # Service-specific details
    
    class Config:
        extra = "allow"


class ExecutionData(BaseModel):
    """Data stored in StrategyExecution.data JSONB"""
    trigger: str  # 'scheduled', 'manual', 'dry_run'
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    result: Optional[Any] = None  # Return value from strategy
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
    file_ids: List[str]
    entrypoint: str = "strategy.py"
    schedule: Optional[str] = None
    schedule_description: Optional[str] = None
    risk_limits: Optional[RiskLimits] = None
    source_chat_id: Optional[str] = None


class UpdateStrategyRequest(BaseModel):
    """Request to update a strategy"""
    name: Optional[str] = None
    enabled: Optional[bool] = None
    schedule: Optional[str] = None
    schedule_description: Optional[str] = None
    risk_limits: Optional[RiskLimits] = None
    # Allow updating description without touching code
    description: Optional[str] = None


class StrategyResponse(BaseModel):
    """Strategy response for API (user-facing, no code details)"""
    id: str
    name: str
    description: str
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
    """Detailed strategy response (includes config for admin/debug)"""
    source_chat_id: Optional[str] = None
    file_ids: List[str] = []
    entrypoint: str = "strategy.py"
    schedule: Optional[str] = None
    risk_limits: Optional[RiskLimits] = None
    stats: StrategyStats = Field(default_factory=StrategyStats)


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
# LLM Tool models (what the LLM sees/uses)
# ============================================================================

class StrategyInfoForLLM(BaseModel):
    """Strategy info formatted for LLM context"""
    id: str
    name: str
    description: str
    status: str  # 'active', 'paused', 'needs_approval', 'never_run'
    schedule: Optional[str] = None  # Human-readable
    last_run: Optional[str] = None  # Human-readable summary
    
    @classmethod
    def from_strategy(cls, strategy) -> "StrategyInfoForLLM":
        """Build from Strategy ORM object"""
        config = strategy.config or {}
        stats = strategy.stats or {}
        
        # Determine status
        if not strategy.approved:
            status = "needs_approval"
        elif not strategy.enabled:
            status = "paused"
        elif stats.get("total_runs", 0) == 0:
            status = "never_run"
        else:
            status = "active"
        
        # Build last run description
        last_run = None
        if stats.get("last_run_at"):
            last_run = f"{stats.get('last_run_status', 'unknown')}: {stats.get('last_run_summary', 'No summary')}"
        
        return cls(
            id=strategy.id,
            name=strategy.name,
            description=config.get("description", ""),
            status=status,
            schedule=config.get("schedule_description"),
            last_run=last_run
        )
