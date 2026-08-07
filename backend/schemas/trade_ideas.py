"""
Trade-idea schemas.

An idea is a catalyst + a thesis + levels + a horizon. It's scored on that
horizon whether or not it was ever approved or executed, which is what makes
the hit-rate numbers meaningful.
"""
from datetime import datetime
from typing import List, Optional, Literal, Dict, Any

from pydantic import BaseModel, Field, model_validator

Direction = Literal["long", "short"]
IdeaStatus = Literal["proposed", "approved", "rejected"]
IdeaOutcome = Literal["pending", "target", "stop", "expired"]
ExecutionMode = Literal["auto", "manual"]

# Kept deliberately coarse — these are the buckets we want hit rates for.
CATALYST_TYPES = [
    "earnings_beat", "earnings_miss", "guidance_raise", "guidance_cut",
    "analyst_upgrade", "analyst_downgrade", "m_and_a", "fda", "contract_win",
    "product_launch", "legal_regulatory", "insider_buying", "index_inclusion",
    "macro", "other",
]


class IdeaCreate(BaseModel):
    symbol: str = Field(description="Ticker, e.g. 'NVDA'")
    catalyst_type: str = Field(description=f"One of: {', '.join(CATALYST_TYPES)}")
    catalyst_summary: str = Field(description="The specific headline, quoted — not a paraphrase")
    thesis: str = Field(description="Why this moves the stock over the horizon")
    entry_ref: float = Field(gt=0, description="Price right now — the scoring reference, not a fill")
    stop: float = Field(gt=0, description="Level that invalidates the thesis")
    target: float = Field(gt=0, description="Where you'd take profit")
    direction: Direction = "long"
    horizon_days: int = Field(3, ge=1, le=15, description="Trading days to hold before it expires")
    conviction: int = Field(3, ge=1, le=5, description="1 = speculative, 5 = highest")
    bear_case: Optional[str] = Field(None, description="The honest case against — required above conviction 3")
    sources: List[Dict[str, Any]] = Field(default_factory=list, description="[{title, url}] backing the catalyst")

    @model_validator(mode="after")
    def _check_levels(self):
        if self.catalyst_type not in CATALYST_TYPES:
            raise ValueError(f"catalyst_type must be one of {CATALYST_TYPES}")
        if self.direction == "long":
            if not (self.stop < self.entry_ref < self.target):
                raise ValueError("long idea needs stop < entry_ref < target")
        else:
            if not (self.target < self.entry_ref < self.stop):
                raise ValueError("short idea needs target < entry_ref < stop")
        # A high-conviction call with no stated downside is where bad ideas hide.
        if self.conviction > 3 and not (self.bear_case or "").strip():
            raise ValueError("bear_case is required for conviction > 3")
        return self

    @property
    def reward_risk(self) -> float:
        return abs(self.target - self.entry_ref) / abs(self.entry_ref - self.stop)


class IdeaDecision(BaseModel):
    """Approve or reject a proposed idea."""
    approve: bool
    execution_mode: Optional[ExecutionMode] = Field(
        None, description="On approve: 'auto' lets the agent place it, 'manual' means you will"
    )

    @model_validator(mode="after")
    def _mode_required_on_approve(self):
        if self.approve and self.execution_mode is None:
            raise ValueError("execution_mode ('auto' or 'manual') is required when approving")
        return self


class Idea(BaseModel):
    id: str
    user_id: str
    created_at: datetime
    symbol: str
    direction: Direction
    catalyst_type: str
    catalyst_summary: str
    thesis: str
    bear_case: Optional[str] = None
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    entry_ref: float
    stop: float
    target: float
    horizon_days: int
    conviction: int
    status: IdeaStatus
    execution_mode: Optional[ExecutionMode] = None
    decided_at: Optional[datetime] = None
    outcome: IdeaOutcome
    scored_at: Optional[datetime] = None
    exit_price: Optional[float] = None
    return_pct: Optional[float] = None
    benchmark_return_pct: Optional[float] = None
    r_multiple: Optional[float] = None

    @property
    def reward_risk(self) -> float:
        return abs(self.target - self.entry_ref) / abs(self.entry_ref - self.stop)

    @property
    def is_open(self) -> bool:
        return self.outcome == "pending"

    @property
    def alpha_pct(self) -> Optional[float]:
        """Return over the benchmark — the number that says the pick added value."""
        if self.return_pct is None or self.benchmark_return_pct is None:
            return None
        return self.return_pct - self.benchmark_return_pct


class IdeaScorecard(BaseModel):
    """Metrics over a set of ideas. Computed over ALL of them by default, which
    is the point — untraded ideas count."""
    total: int = 0
    open: int = 0
    scored: int = 0
    wins: int = 0
    losses: int = 0
    hit_rate: Optional[float] = None       # wins / scored
    avg_return_pct: Optional[float] = None
    avg_alpha_pct: Optional[float] = None  # vs SPY — the one that matters
    avg_r_multiple: Optional[float] = None


class IdeaList(BaseModel):
    ideas: List[Idea]
    scorecard: IdeaScorecard
    by_catalyst: Dict[str, IdeaScorecard] = Field(
        default_factory=dict,
        description="Same metrics per catalyst_type — tells you which catalysts actually work",
    )
