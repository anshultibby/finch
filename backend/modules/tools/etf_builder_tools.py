"""
Custom ETF Builder Tools

Tools for building and analyzing custom ETF portfolios with different weighting strategies.
"""
from modules.tools import tool
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
    weighting_method: Literal["equal_weight", "market_cap"] = Field(
        "equal_weight",
        description="Weighting strategy: 'equal_weight' (same % for each stock) or 'market_cap' (weighted by market capitalization)"
    )
    name: Optional[str] = Field(
        None,
        description="Optional name for the custom ETF (e.g., 'Tech Leaders ETF', 'Value Picks Q4 2024')"
    )


@tool(
    name="build_custom_etf",
    description="""Build a custom ETF portfolio with specified stocks and weighting strategy.

**What it does:**
- Takes a list of tickers and creates a weighted portfolio
- Supports two weighting methods:
  * equal_weight: Each stock gets equal allocation (e.g., 5 stocks = 20% each)
  * market_cap: Stocks weighted by their market capitalization (larger companies get more weight)
- Fetches current market data (prices, market caps) for all tickers
- Calculates portfolio weights and displays allocation breakdown
- Returns structured portfolio data ready for backtesting

**Use cases:**
- After screening stocks, build a portfolio from the top candidates
- Create thematic portfolios (e.g., "AI stocks", "dividend aristocrats")
- Compare equal-weight vs market-cap weighting strategies
- Prepare portfolios for backtesting and performance analysis

**Example workflow:**
1. User: "Find undervalued tech stocks with P/E < 20"
2. Agent: Writes Python screening code and executes it to get tickers
3. Agent: Calls build_custom_etf with those tickers
4. Agent: Writes backtest code and executes it to analyze performance
5. Agent: Uses create_chart to visualize results

**Returns:** Portfolio composition with weights, prices, and market caps""",
    category="analysis"
)
async def build_custom_etf(
    *,
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
            "message": "Calculating portfolio weights..."
        })
        
        # Calculate weights based on method
        if params.weighting_method == "equal_weight":
            # Equal weight: each stock gets same percentage
            weight = 1.0 / len(portfolio_components)
            for component in portfolio_components:
                component["weight"] = weight
        
        elif params.weighting_method == "market_cap":
            # Market cap weight: weight proportional to market cap
            total_market_cap = sum(c["market_cap"] for c in portfolio_components)
            for component in portfolio_components:
                component["weight"] = component["market_cap"] / total_market_cap
        
        # Sort by weight descending for better display
        portfolio_components.sort(key=lambda x: x["weight"], reverse=True)
        
        yield SSEEvent(event="tool_status", data={
            "status": "complete",
            "message": "✓ Custom ETF built successfully"
        })
        
        # Build result
        etf_name = params.name or f"Custom {params.weighting_method.replace('_', ' ').title()} ETF"
        
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
                "average_weight": f"{(100.0 / len(portfolio_components)):.1f}%" if params.weighting_method == "equal_weight" else "varies"
            },
            "message": f"✓ Built {etf_name} with {len(portfolio_components)} stocks" + 
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


# ============================================================================
# CODE GENERATION GUIDELINES FOR ETF BACKTESTING
# ============================================================================

ETF_BACKTEST_CODE_TEMPLATE = '''"""
Custom ETF Backtest Template

This template shows how to backtest a custom ETF portfolio using FMP historical data.
The agent can use this as a reference when generating backtest code.
"""
import os
import requests
from datetime import datetime, timedelta
import pandas as pd

def fetch_historical_data(ticker, start_date, end_date, api_key):
    """Fetch historical price data from FMP"""
    url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{ticker}"
    params = {
        "apikey": api_key,
        "from": start_date,
        "to": end_date
    }
    response = requests.get(url, params=params)
    data = response.json()
    
    if "historical" not in data:
        return None
    
    df = pd.DataFrame(data["historical"])
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")
    return df[["date", "close"]]


def backtest_custom_etf(portfolio_components, start_date, end_date):
    """
    Backtest a custom ETF portfolio
    
    Args:
        portfolio_components: List of dicts with 'ticker' and 'weight'
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
    
    Returns:
        DataFrame with portfolio value over time
    """
    api_key = os.getenv("FMP_API_KEY")
    
    # Fetch data for all components
    print(f"Fetching historical data for {len(portfolio_components)} stocks...")
    
    stock_data = {}
    for component in portfolio_components:
        ticker = component["ticker"]
        weight = component["weight"]
        
        df = fetch_historical_data(ticker, start_date, end_date, api_key)
        if df is not None:
            df["ticker"] = ticker
            df["weight"] = weight
            stock_data[ticker] = df
            print(f"✓ {ticker}: {len(df)} trading days")
        else:
            print(f"✗ {ticker}: No data available")
    
    if not stock_data:
        print("ERROR: No historical data available for any stocks")
        return None
    
    # Combine all data and calculate portfolio value
    all_dates = set()
    for df in stock_data.values():
        all_dates.update(df["date"].tolist())
    
    all_dates = sorted(all_dates)
    
    # Calculate portfolio returns
    portfolio_values = []
    initial_value = 10000  # Start with $10,000
    
    for date in all_dates:
        daily_return = 0
        weights_sum = 0
        
        for ticker, df in stock_data.items():
            date_data = df[df["date"] == date]
            if not date_data.empty:
                weight = df["weight"].iloc[0]
                
                # Calculate return since start
                first_price = df["close"].iloc[0]
                current_price = date_data["close"].iloc[0]
                stock_return = (current_price - first_price) / first_price
                
                daily_return += weight * stock_return
                weights_sum += weight
        
        if weights_sum > 0:
            # Normalize by actual weights present
            daily_return = daily_return / weights_sum
            portfolio_value = initial_value * (1 + daily_return)
            portfolio_values.append({
                "date": date,
                "value": portfolio_value,
                "return": daily_return * 100
            })
    
    result_df = pd.DataFrame(portfolio_values)
    
    # Calculate performance metrics
    total_return = ((result_df["value"].iloc[-1] - initial_value) / initial_value) * 100
    days = (result_df["date"].iloc[-1] - result_df["date"].iloc[0]).days
    annualized_return = (pow(result_df["value"].iloc[-1] / initial_value, 365.0 / days) - 1) * 100
    
    print("\\n" + "="*60)
    print("BACKTEST RESULTS")
    print("="*60)
    print(f"Period: {result_df['date'].iloc[0].date()} to {result_df['date'].iloc[-1].date()}")
    print(f"Trading Days: {len(result_df)}")
    print(f"Initial Value: ${initial_value:,.2f}")
    print(f"Final Value: ${result_df['value'].iloc[-1]:,.2f}")
    print(f"Total Return: {total_return:+.2f}%")
    print(f"Annualized Return: {annualized_return:+.2f}%")
    print(f"Max Value: ${result_df['value'].max():,.2f}")
    print(f"Min Value: ${result_df['value'].min():,.2f}")
    print("="*60)
    
    return result_df


# Example usage
if __name__ == "__main__":
    # Define your custom ETF components (from build_custom_etf output)
    portfolio = [
        {"ticker": "AAPL", "weight": 0.25},
        {"ticker": "MSFT", "weight": 0.25},
        {"ticker": "GOOGL", "weight": 0.25},
        {"ticker": "NVDA", "weight": 0.25}
    ]
    
    # Backtest over the last year
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    
    results = backtest_custom_etf(portfolio, start_date, end_date)
    
    # Print daily results sample
    if results is not None:
        print("\\nSample data (first 10 days):")
        print(results.head(10).to_string(index=False))
'''


def get_etf_backtest_guidelines() -> str:
    """
    Get guidelines for the agent on how to backtest custom ETFs
    
    Returns:
        String with guidelines and code template
    """
    return f"""
**Custom ETF Backtesting Guidelines:**

When a user wants to backtest a custom ETF:

1. **Build the ETF first** using build_custom_etf:
   - Get list of tickers (from screening or user input)
   - Choose weighting method (equal_weight or market_cap)
   - Call build_custom_etf to get portfolio composition

2. **Write backtest code** using write_chat_file:
   - Use the portfolio components from build_custom_etf output
   - Fetch historical data for each ticker using FMP API
   - Calculate weighted returns over time
   - Compute performance metrics (total return, annualized return, max/min values)
   - Format and print results

3. **Execute the backtest** using execute_code:
   - Run the backtest code
   - Capture results

4. **Visualize performance** using create_chart:
   - Plot portfolio value over time
   - Optionally add benchmark (e.g., SPY) for comparison
   - Add trendline if useful

**Code Template Reference:**

{ETF_BACKTEST_CODE_TEMPLATE}

**Key Points:**
- Use FMP's historical-price-full endpoint for historical data
- Start with $10,000 initial portfolio value (industry standard)
- Calculate both total return and annualized return
- Handle missing data gracefully (some tickers may not have full history)
- Print clear results table with metrics
"""

