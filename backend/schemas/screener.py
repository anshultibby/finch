"""
Stock screener schemas — a `ScreenSpec` is the shared contract: the AI emits it
from natural language, the UI edits it, and the runner executes it against FMP.
Keep field names aligned with FMP's /stock-screener params so the mapping stays
trivial and transparent.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Literal


class ScreenFilters(BaseModel):
    """Numeric/categorical filters. All optional — only set fields are applied."""
    marketCapMoreThan: Optional[int] = Field(None, description="Min market cap in USD")
    marketCapLowerThan: Optional[int] = Field(None, description="Max market cap in USD")
    priceMoreThan: Optional[float] = Field(None, description="Min share price")
    priceLowerThan: Optional[float] = Field(None, description="Max share price")
    betaMoreThan: Optional[float] = Field(None, description="Min beta")
    betaLowerThan: Optional[float] = Field(None, description="Max beta")
    volumeMoreThan: Optional[int] = Field(None, description="Min average volume")
    volumeLowerThan: Optional[int] = Field(None, description="Max average volume")
    dividendMoreThan: Optional[float] = Field(None, description="Min last annual dividend ($/share)")
    dividendLowerThan: Optional[float] = Field(None, description="Max last annual dividend ($/share)")
    sector: Optional[str] = Field(None, description="e.g. Technology, Healthcare, Energy")
    industry: Optional[str] = Field(None, description="e.g. Semiconductors")
    country: Optional[str] = Field(None, description="ISO country, e.g. US")
    exchange: Optional[str] = Field(None, description="e.g. NASDAQ, NYSE")
    isEtf: Optional[bool] = None
    isFund: Optional[bool] = None
    isActivelyTrading: Optional[bool] = True


class ScreenSpec(BaseModel):
    """A complete, runnable screen definition."""
    name: Optional[str] = Field(None, description="Human-friendly name, e.g. 'Cheap dividend tech'")
    description: Optional[str] = Field(None, description="What this screen is looking for")
    filters: ScreenFilters = Field(default_factory=ScreenFilters)
    sortBy: Literal[
        "marketCap", "price", "beta", "volume", "dividend", "companyName"
    ] = "marketCap"
    sortDir: Literal["asc", "desc"] = "desc"
    limit: int = Field(25, ge=1, le=100)


class ScreenRow(BaseModel):
    symbol: str
    companyName: Optional[str] = None
    marketCap: Optional[int] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    beta: Optional[float] = None
    price: Optional[float] = None
    lastAnnualDividend: Optional[float] = None
    volume: Optional[int] = None
    exchangeShortName: Optional[str] = None
    isEtf: Optional[bool] = None


class ScreenResponse(BaseModel):
    spec: ScreenSpec
    count: int
    results: List[ScreenRow]
