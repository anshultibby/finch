"""
Portfolio analytics schemas. The view is computed from a list of holdings the
client already has (symbol + market value), enriched with sector/beta/dividend
from FMP, then narrated by the AI.
"""
from pydantic import BaseModel, Field
from typing import List, Optional


class Holding(BaseModel):
    symbol: str
    value: float = Field(description="Market value of the position in USD")


class AnalyzeRequest(BaseModel):
    holdings: List[Holding]
    narrate: bool = True


class Allocation(BaseModel):
    label: str
    value: float
    weight: float  # 0..1


class TopHolding(BaseModel):
    symbol: str
    value: float
    weight: float
    sector: Optional[str] = None
    beta: Optional[float] = None


class AnalyticsView(BaseModel):
    total_value: float
    holding_count: int
    sector_allocation: List[Allocation]
    top_holdings: List[TopHolding]
    top5_concentration: float          # 0..1 — weight of largest 5 positions
    largest_position_weight: float     # 0..1
    weighted_beta: Optional[float] = None
    annual_dividend_income: float
    dividend_yield: float              # 0..1
    enriched_count: int                # how many holdings we got fundamentals for
    narration: Optional[str] = None
