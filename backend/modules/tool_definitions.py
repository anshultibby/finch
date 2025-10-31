"""
Central tool definitions file
All LLM-callable tools are defined here using the @tool decorator
"""
from typing import Dict, Any, List, Optional
from modules.tools import tool, ToolContext, tool_registry

# Import business logic modules
from modules.snaptrade_tools import snaptrade_tools
from modules.apewisdom_tools import apewisdom_tools
from modules.insider_trading_tools import insider_trading_tools


# ============================================================================
# PORTFOLIO TOOLS (SnapTrade)
# ============================================================================

@tool(
    description="Fetch the user's current brokerage portfolio holdings (Robinhood, TD Ameritrade, etc.), including stocks they own, quantities, current prices, and total value. Returns data in efficient CSV format: holdings_csv contains all unique positions aggregated across accounts. ALWAYS call this tool first when the user asks about their portfolio, stocks, holdings, or account value. This tool will automatically handle authentication - if the user isn't connected, it will tell you to request connection. Do not guess or assume - call this tool to check.",
    category="portfolio",
    requires_auth=True
)
def get_portfolio(
    *,
    context: ToolContext
) -> Dict[str, Any]:
    """Get user's portfolio holdings"""
    if not context.session_id:
        return {
            "success": False,
            "message": "Session ID required",
            "needs_auth": True
        }
    
    return snaptrade_tools.get_portfolio(session_id=context.session_id)


@tool(
    description="Request the user to connect their brokerage account via SnapTrade. ONLY use this tool if get_portfolio returns an authentication error. Do NOT call this proactively - always try get_portfolio first.",
    category="portfolio",
    requires_auth=False
)
def request_brokerage_connection(
    *,
    context: ToolContext
) -> Dict[str, Any]:
    """Request user to connect their brokerage account"""
    return {
        "success": True,
        "needs_auth": True,
        "message": "Please connect your brokerage account through SnapTrade to continue.",
        "action_required": "show_connection_modal"
    }


# ============================================================================
# REDDIT SENTIMENT TOOLS (ApeWisdom)
# ============================================================================

@tool(
    description="Get the most talked about and trending stocks from Reddit communities like r/wallstreetbets, r/stocks, and r/investing. Shows current mentions, upvotes, and ranking. Use this when user asks about what's popular/trending on Reddit, what stocks Reddit is talking about, or meme stocks.",
    category="reddit_sentiment"
)
async def get_reddit_trending_stocks(
    *,
    context: ToolContext,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Get trending stocks from Reddit communities
    
    Args:
        limit: Number of trending stocks to return (default 10, max 50)
    """
    return await apewisdom_tools.get_trending_stocks(limit=limit)


@tool(
    description="Get Reddit sentiment and mentions for a specific stock ticker. Shows how many times it's been mentioned, upvotes, rank, and 24h change. Use this when user asks about Reddit sentiment for a specific stock.",
    category="reddit_sentiment"
)
async def get_reddit_ticker_sentiment(
    *,
    context: ToolContext,
    ticker: str
) -> Dict[str, Any]:
    """
    Get Reddit sentiment for a specific stock ticker
    
    Args:
        ticker: Stock ticker symbol (e.g., 'GME', 'TSLA', 'AAPL')
    """
    return await apewisdom_tools.get_ticker_sentiment(ticker=ticker)


@tool(
    description="Compare Reddit sentiment for multiple stock tickers. Shows which stocks are more popular on Reddit. Use this when user wants to compare multiple stocks or asks which one Reddit prefers.",
    category="reddit_sentiment"
)
async def compare_reddit_sentiment(
    *,
    context: ToolContext,
    tickers: List[str]
) -> Dict[str, Any]:
    """
    Compare Reddit sentiment for multiple tickers
    
    Args:
        tickers: List of ticker symbols to compare (e.g., ['GME', 'AMC', 'TSLA'])
    """
    return await apewisdom_tools.compare_tickers_sentiment(tickers=tickers)


# ============================================================================
# INSIDER TRADING TOOLS (Financial Modeling Prep)
# ============================================================================

@tool(
    description="Get recent stock trading disclosures from U.S. Senators. Shows what stocks senators are buying and selling. Use when user asks about Senate trades, congressional trades, or what politicians are buying.",
    category="insider_trading"
)
async def get_recent_senate_trades(
    *,
    context: ToolContext,
    limit: int = 50
) -> Dict[str, Any]:
    """
    Get recent Senate trading disclosures
    
    Args:
        limit: Number of recent trades to return (default 50, max 100)
    """
    return await insider_trading_tools.get_recent_senate_trades(limit=limit)


@tool(
    description="Get recent stock trading disclosures from U.S. House Representatives. Shows what stocks house members are buying and selling. Use when user asks about House trades or congressional activity.",
    category="insider_trading"
)
async def get_recent_house_trades(
    *,
    context: ToolContext,
    limit: int = 50
) -> Dict[str, Any]:
    """
    Get recent House trading disclosures
    
    Args:
        limit: Number of recent trades to return (default 50, max 100)
    """
    return await insider_trading_tools.get_recent_house_trades(limit=limit)


@tool(
    description="Get recent corporate insider trades (SEC Form 4 filings). Shows what company executives, directors, and major shareholders are buying and selling. Use when user asks about insider trades, insider buying/selling, or Form 4 filings.",
    category="insider_trading"
)
async def get_recent_insider_trades(
    *,
    context: ToolContext,
    limit: int = 100
) -> Dict[str, Any]:
    """
    Get recent corporate insider trades (SEC Form 4 filings)
    
    Args:
        limit: Number of recent trades to return (default 100, max 200)
    """
    return await insider_trading_tools.get_recent_insider_trades(limit=limit)


@tool(
    description="Search for all insider trading activity (Senate, House, and corporate insiders) for a specific stock ticker. Use when user asks about insider activity for a particular stock.",
    category="insider_trading"
)
async def search_ticker_insider_activity(
    *,
    context: ToolContext,
    ticker: str,
    limit: int = 50
) -> Dict[str, Any]:
    """
    Search for all insider trading activity for a specific ticker
    
    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'TSLA', 'NVDA')
        limit: Maximum trades to return per source (default 50)
    """
    return await insider_trading_tools.search_ticker_insider_activity(ticker=ticker, limit=limit)


@tool(
    description="Get insider trading activity for stocks in the user's portfolio. Shows which portfolio stocks have recent insider/congressional activity. REQUIRES get_portfolio to be called first to get the list of tickers.",
    category="insider_trading",
    requires_auth=True
)
async def get_portfolio_insider_activity(
    *,
    context: ToolContext,
    tickers: List[str],
    days_back: int = 30
) -> Dict[str, Any]:
    """
    Get insider trading activity for multiple tickers (user's portfolio)
    
    Args:
        tickers: List of ticker symbols from user's portfolio
        days_back: Look back this many days for activity (default 30)
    """
    # Limit to max 20 tickers to avoid overwhelming API/response
    if len(tickers) > 20:
        print(f"⚠️ Limiting tickers from {len(tickers)} to 20 to avoid overload", flush=True)
        tickers = tickers[:20]
    
    return await insider_trading_tools.get_portfolio_insider_activity(tickers=tickers, days_back=days_back)


@tool(
    description="Get quarterly aggregated insider trading statistics for a specific stock. Shows historical trends of insider buying vs selling over time, including buy/sell ratios, average transaction sizes, and patterns. Useful for analyzing long-term insider sentiment.",
    category="insider_trading"
)
async def get_insider_trading_statistics(
    *,
    context: ToolContext,
    symbol: str
) -> Dict[str, Any]:
    """
    Get quarterly aggregated insider trading statistics for a specific stock
    
    Args:
        symbol: Stock ticker symbol (e.g., 'AAPL', 'TSLA')
    """
    return await insider_trading_tools.get_insider_trading_statistics(symbol=symbol)


@tool(
    description="Search insider trades with advanced filters. Filter by specific stock, insider CIK, company CIK, or transaction type (P-Purchase, S-Sale, A-Award, etc.). Useful for finding specific patterns or tracking particular insiders.",
    category="insider_trading"
)
async def search_insider_trades(
    *,
    context: ToolContext,
    symbol: Optional[str] = None,
    reporting_cik: Optional[str] = None,
    company_cik: Optional[str] = None,
    transaction_type: Optional[str] = None,
    limit: int = 50,
    page: int = 0
) -> Dict[str, Any]:
    """
    Search insider trades with advanced filters
    
    Args:
        symbol: Stock ticker symbol to filter by (optional)
        reporting_cik: CIK of the person reporting (insider) to filter by (optional)
        company_cik: CIK of the company to filter by (optional)
        transaction_type: Transaction type: P-Purchase, S-Sale, A-Award, M-Exempt, etc. (optional)
        limit: Number of results to return (default 50, max 100)
        page: Page number for pagination (default 0)
    """
    return await insider_trading_tools.search_insider_trades(
        symbol=symbol,
        reporting_cik=reporting_cik,
        company_cik=company_cik,
        transaction_type=transaction_type,
        limit=limit,
        page=page
    )


# ============================================================================
# REGISTER ALL TOOLS
# ============================================================================

def register_all_tools():
    """Register all tools with the global registry"""
    # Portfolio tools
    tool_registry.register_function(get_portfolio)
    tool_registry.register_function(request_brokerage_connection)
    
    # Reddit sentiment tools
    tool_registry.register_function(get_reddit_trending_stocks)
    tool_registry.register_function(get_reddit_ticker_sentiment)
    tool_registry.register_function(compare_reddit_sentiment)
    
    # Insider trading tools
    tool_registry.register_function(get_recent_senate_trades)
    tool_registry.register_function(get_recent_house_trades)
    tool_registry.register_function(get_recent_insider_trades)
    tool_registry.register_function(search_ticker_insider_activity)
    tool_registry.register_function(get_portfolio_insider_activity)
    tool_registry.register_function(get_insider_trading_statistics)
    tool_registry.register_function(search_insider_trades)


# Auto-register on import
register_all_tools()

