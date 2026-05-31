"""
Stock screener tool implementation — lets the agent run a screen from a flat set
of filter params. The agent compiles a user's natural-language request into these
params, runs the screen, then reasons over the returned rows.
"""
from typing import Optional, Literal
from pydantic import BaseModel, Field

from schemas.screener import ScreenSpec, ScreenFilters
from services.screener import run_screen


class RunScreenParams(BaseModel):
    """Flat filter params. Only set what's relevant — everything is optional."""
    market_cap_min: Optional[int] = Field(None, description="Min market cap in USD (e.g. 2000000000 = $2B)")
    market_cap_max: Optional[int] = Field(None, description="Max market cap in USD")
    price_min: Optional[float] = Field(None, description="Min share price")
    price_max: Optional[float] = Field(None, description="Max share price")
    beta_min: Optional[float] = Field(None, description="Min beta (volatility vs market)")
    beta_max: Optional[float] = Field(None, description="Max beta")
    volume_min: Optional[int] = Field(None, description="Min average daily volume")
    dividend_min: Optional[float] = Field(None, description="Min last annual dividend per share ($)")
    sector: Optional[str] = Field(None, description="Sector, e.g. Technology, Healthcare, Energy, Financial Services")
    industry: Optional[str] = Field(None, description="Industry, e.g. Semiconductors")
    country: Optional[str] = Field("US", description="ISO country code, default US")
    exchange: Optional[str] = Field(None, description="Exchange, e.g. NASDAQ, NYSE")
    is_etf: Optional[bool] = Field(None, description="Restrict to ETFs (true) or exclude them (false)")
    sort_by: Literal["marketCap", "price", "beta", "volume", "dividend", "companyName"] = "marketCap"
    sort_dir: Literal["asc", "desc"] = "desc"
    limit: int = Field(25, ge=1, le=100)
    name: Optional[str] = Field(None, description="Short name for this screen")


def run_stock_screen_impl(params: RunScreenParams, context) -> dict:
    spec = ScreenSpec(
        name=params.name,
        filters=ScreenFilters(
            marketCapMoreThan=params.market_cap_min,
            marketCapLowerThan=params.market_cap_max,
            priceMoreThan=params.price_min,
            priceLowerThan=params.price_max,
            betaMoreThan=params.beta_min,
            betaLowerThan=params.beta_max,
            volumeMoreThan=params.volume_min,
            dividendMoreThan=params.dividend_min,
            sector=params.sector,
            industry=params.industry,
            country=params.country,
            exchange=params.exchange,
            isEtf=params.is_etf,
        ),
        sortBy=params.sort_by,
        sortDir=params.sort_dir,
        limit=params.limit,
    )
    rows = run_screen(spec)
    return {
        "spec": spec.model_dump(exclude_none=True),
        "count": len(rows),
        "results": [r.model_dump(exclude_none=True) for r in rows],
    }
