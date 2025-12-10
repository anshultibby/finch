"""
Custom ETF Builder Implementation

Tools for building and analyzing custom ETF portfolios with different weighting strategies.
"""
from modules.agent.context import AgentContext
from models.sse import SSEEvent
from typing import Optional, Dict, Any, AsyncGenerator, List, Literal
from pydantic import BaseModel, Field
from utils.logger import get_logger
import os

logger = get_logger(__name__)


class BuildCustomETFParams(BaseModel):
    """Build a custom ETF with specified stocks and weighting strategy"""
    tickers: List[str] = Field(
        ...,
        description="List of stock tickers to include in the ETF (e.g., ['AAPL', 'MSFT', 'GOOGL'])"
    )
    weighting_method: Literal["market_cap"] = Field(
        "market_cap",
        description="Weighting strategy: 'market_cap' (weighted by market capitalization). Note: For now, only market cap weighting is supported."
    )
    name: Optional[str] = Field(
        None,
        description="Optional name for the custom ETF (e.g., 'Tech Leaders ETF', 'Value Picks Q4 2024')"
    )


async def build_custom_etf_impl(
    params: BuildCustomETFParams,
    context: AgentContext
) -> AsyncGenerator[SSEEvent | Dict[str, Any], None]:
    """Build a custom ETF portfolio"""
    import httpx
    from config import Config
    
    logger.info(f"Building custom ETF with {len(params.tickers)} tickers using {params.weighting_method}")
    
    yield SSEEvent(event="tool_status", data={
        "status": "loading",
        "message": f"Fetching market data for {len(params.tickers)} stocks..."
    })
    
    try:
        # Fetch market data for all tickers
        api_key = Config.FMP_API_KEY
        if not api_key:
            yield {"success": False, "error": "FMP_API_KEY not configured"}
            return
        
        portfolio_components = []
        failed_tickers = []
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for ticker in params.tickers:
                try:
                    # Fetch quote data for current price and market cap
                    url = f"https://financialmodelingprep.com/api/v3/quote/{ticker}"
                    response = await client.get(url, params={"apikey": api_key})
                    response.raise_for_status()
                    data = response.json()
                    
                    if not data or len(data) == 0:
                        logger.warning(f"No data returned for ticker {ticker}")
                        failed_tickers.append(ticker)
                        continue
                    
                    quote = data[0]
                    
                    # Extract key data
                    market_cap = quote.get("marketCap", 0)
                    price = quote.get("price", 0)
                    name = quote.get("name", ticker)
                    
                    if market_cap <= 0 or price <= 0:
                        logger.warning(f"Invalid data for {ticker}: market_cap={market_cap}, price={price}")
                        failed_tickers.append(ticker)
                        continue
                    
                    portfolio_components.append({
                        "ticker": ticker,
                        "name": name,
                        "price": price,
                        "market_cap": market_cap,
                        "weight": 0.0  # Will be calculated below
                    })
                
                except Exception as e:
                    logger.warning(f"Failed to fetch data for {ticker}: {e}")
                    failed_tickers.append(ticker)
        
        if not portfolio_components:
            yield {
                "success": False,
                "error": "Failed to fetch data for any tickers. Check that ticker symbols are valid."
            }
            return
        
        yield SSEEvent(event="tool_status", data={
            "status": "calculating",
            "message": "Calculating portfolio weights by market cap..."
        })
        
        # Calculate weights by market cap
        # Market cap weight: weight proportional to market cap
        total_market_cap = sum(c["market_cap"] for c in portfolio_components)
        for component in portfolio_components:
            component["weight"] = component["market_cap"] / total_market_cap
        
        # Sort by weight descending for better display
        portfolio_components.sort(key=lambda x: x["weight"], reverse=True)
        
        yield SSEEvent(event="tool_status", data={
            "status": "complete",
            "message": "Custom ETF built successfully"
        })
        
        # Build result
        etf_name = params.name or "Custom Market Cap Weighted ETF"
        
        result = {
            "success": True,
            "etf_name": etf_name,
            "weighting_method": params.weighting_method,
            "total_stocks": len(portfolio_components),
            "failed_tickers": failed_tickers if failed_tickers else None,
            "components": portfolio_components,
            "summary": {
                "top_holding": portfolio_components[0]["ticker"] if portfolio_components else None,
                "top_weight": f"{portfolio_components[0]['weight']*100:.1f}%" if portfolio_components else None,
                "total_market_cap": sum(c["market_cap"] for c in portfolio_components),
                "weighting": "market_cap"
            },
            "message": f"Built {etf_name} with {len(portfolio_components)} stocks (weighted by market cap)" + 
                      (f" ({len(failed_tickers)} failed)" if failed_tickers else "")
        }
        
        # Create a formatted table for display
        table_rows = []
        for comp in portfolio_components:
            table_rows.append({
                "Ticker": comp["ticker"],
                "Name": comp["name"][:30],  # Truncate long names
                "Weight": f"{comp['weight']*100:.2f}%",
                "Price": f"${comp['price']:.2f}",
                "Market Cap": f"${comp['market_cap']/1e9:.1f}B"
            })
        
        result["table"] = table_rows
        
        yield result
    
    except Exception as e:
        logger.error(f"Error building custom ETF: {e}", exc_info=True)
        yield {"success": False, "error": str(e)}
