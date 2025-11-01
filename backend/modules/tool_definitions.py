"""
Central tool definitions file
All LLM-callable tools are defined here using the @tool decorator
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from modules.tools import tool, ToolContext, tool_registry

# Import business logic modules
from modules.snaptrade_tools import snaptrade_tools
from modules.apewisdom_tools import apewisdom_tools
from modules.insider_trading_tools import insider_trading_tools
from modules.fmp_tools import fmp_tools
from modules.agent.plotting_agent import plotting_agent
from modules.agent.financial_metrics_agent import financial_metrics_agent

# Import plotting tools (for sub-agent)
from modules.plotting_tools import create_chart

# Import tool descriptions
from modules.tool_descriptions import (
    # Portfolio
    GET_PORTFOLIO_DESC, REQUEST_BROKERAGE_CONNECTION_DESC,
    # Reddit sentiment
    GET_REDDIT_TRENDING_DESC, GET_REDDIT_TICKER_SENTIMENT_DESC, COMPARE_REDDIT_SENTIMENT_DESC,
    # Insider trading
    GET_SENATE_TRADES_DESC, GET_HOUSE_TRADES_DESC, GET_INSIDER_TRADES_DESC,
    SEARCH_TICKER_INSIDER_DESC, GET_PORTFOLIO_INSIDER_DESC, GET_INSIDER_STATISTICS_DESC,
    SEARCH_INSIDER_TRADES_DESC,
    # Financial metrics
    GET_COMPANY_PROFILE_DESC, GET_INCOME_STATEMENT_DESC, GET_BALANCE_SHEET_DESC,
    GET_CASH_FLOW_DESC, GET_KEY_METRICS_DESC, GET_FINANCIAL_RATIOS_DESC,
    GET_FINANCIAL_GROWTH_DESC, GET_QUOTE_DESC, GET_HISTORICAL_PRICES_DESC,
    GET_ANALYST_RECOMMENDATIONS_DESC,
    # Screening & search
    SCREEN_STOCKS_DESC,
    # Market movers
    GET_TOP_GAINERS_DESC, GET_TOP_LOSERS_DESC, GET_MOST_ACTIVE_DESC,
    GET_SECTOR_PERFORMANCE_DESC,
    # News
    GET_STOCK_NEWS_DESC,
    # ETF
    GET_ETF_HOLDINGS_DESC, GET_ETF_INFO_DESC,
    # Corporate events
    GET_EARNINGS_CALENDAR_DESC, GET_DIVIDENDS_CALENDAR_DESC,
    # Analyst data
    GET_PRICE_TARGET_DESC, GET_UPGRADES_DOWNGRADES_DESC,
    # Comparisons
    GET_PEER_COMPANIES_DESC,
    # ESG
    GET_ESG_SCORES_DESC,
    # SEC filings
    GET_SEC_FILINGS_DESC,
    # Financial analysis agent
    ANALYZE_FINANCIALS_DESC,
    # Visualization
    CREATE_PLOT_DESC
)


# ============================================================================
# PORTFOLIO TOOLS (SnapTrade)
# ============================================================================

@tool(
    description=GET_PORTFOLIO_DESC,
    category="portfolio",
    requires_auth=True
)
def get_portfolio(
    *,
    context: ToolContext
) -> Dict[str, Any]:
    """Get user's portfolio holdings"""
    if not context.user_id:
        return {
            "success": False,
            "message": "User ID required",
            "needs_auth": True
        }
    
    return snaptrade_tools.get_portfolio(user_id=context.user_id)


@tool(
    description=REQUEST_BROKERAGE_CONNECTION_DESC,
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
    description=GET_REDDIT_TRENDING_DESC,
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
    description=GET_REDDIT_TICKER_SENTIMENT_DESC,
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
    description=COMPARE_REDDIT_SENTIMENT_DESC,
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
    description=GET_SENATE_TRADES_DESC,
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
    description=GET_HOUSE_TRADES_DESC,
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
    description=GET_INSIDER_TRADES_DESC,
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
    description=SEARCH_TICKER_INSIDER_DESC,
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
    description=GET_PORTFOLIO_INSIDER_DESC,
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
    description=GET_INSIDER_STATISTICS_DESC,
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
    description=SEARCH_INSIDER_TRADES_DESC,
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
# FINANCIAL METRICS TOOLS (Financial Modeling Prep)
# ============================================================================

@tool(
    description=GET_COMPANY_PROFILE_DESC,
    category="financial_metrics"
)
async def get_company_profile(
    *,
    context: ToolContext,
    symbol: str
) -> Dict[str, Any]:
    """
    Get comprehensive company profile and information
    
    Args:
        symbol: Stock ticker symbol (e.g., 'AAPL', 'TSLA', 'NVDA')
    """
    return await fmp_tools.get_company_profile(symbol=symbol)


@tool(
    description=GET_INCOME_STATEMENT_DESC,
    category="financial_metrics"
)
async def get_income_statement(
    *,
    context: ToolContext,
    symbol: str,
    period: str = "annual",
    limit: int = 10
) -> Dict[str, Any]:
    """
    Get income statement data
    
    Args:
        symbol: Stock ticker symbol (e.g., 'AAPL', 'TSLA')
        period: 'annual' or 'quarter' (default 'annual')
        limit: Number of periods to return (default 10)
    """
    return await fmp_tools.get_income_statement(symbol=symbol, period=period, limit=limit)


@tool(
    description=GET_BALANCE_SHEET_DESC,
    category="financial_metrics"
)
async def get_balance_sheet(
    *,
    context: ToolContext,
    symbol: str,
    period: str = "annual",
    limit: int = 10
) -> Dict[str, Any]:
    """
    Get balance sheet data
    
    Args:
        symbol: Stock ticker symbol (e.g., 'AAPL', 'TSLA')
        period: 'annual' or 'quarter' (default 'annual')
        limit: Number of periods to return (default 10)
    """
    return await fmp_tools.get_balance_sheet(symbol=symbol, period=period, limit=limit)


@tool(
    description=GET_CASH_FLOW_DESC,
    category="financial_metrics"
)
async def get_cash_flow_statement(
    *,
    context: ToolContext,
    symbol: str,
    period: str = "annual",
    limit: int = 10
) -> Dict[str, Any]:
    """
    Get cash flow statement data
    
    Args:
        symbol: Stock ticker symbol (e.g., 'AAPL', 'TSLA')
        period: 'annual' or 'quarter' (default 'annual')
        limit: Number of periods to return (default 10)
    """
    return await fmp_tools.get_cash_flow_statement(symbol=symbol, period=period, limit=limit)


@tool(
    description=GET_KEY_METRICS_DESC,
    category="financial_metrics"
)
async def get_key_metrics(
    *,
    context: ToolContext,
    symbol: str,
    period: str = "annual",
    limit: int = 10
) -> Dict[str, Any]:
    """
    Get key metrics and valuation ratios
    
    Args:
        symbol: Stock ticker symbol (e.g., 'AAPL', 'TSLA')
        period: 'annual' or 'quarter' (default 'annual')
        limit: Number of periods to return (default 10)
    """
    return await fmp_tools.get_key_metrics(symbol=symbol, period=period, limit=limit)


@tool(
    description=GET_FINANCIAL_RATIOS_DESC,
    category="financial_metrics"
)
async def get_financial_ratios(
    *,
    context: ToolContext,
    symbol: str,
    period: str = "annual",
    limit: int = 10
) -> Dict[str, Any]:
    """
    Get financial ratios
    
    Args:
        symbol: Stock ticker symbol (e.g., 'AAPL', 'TSLA')
        period: 'annual' or 'quarter' (default 'annual')
        limit: Number of periods to return (default 10)
    """
    return await fmp_tools.get_financial_ratios(symbol=symbol, period=period, limit=limit)


@tool(
    description=GET_FINANCIAL_GROWTH_DESC,
    category="financial_metrics"
)
async def get_financial_growth(
    *,
    context: ToolContext,
    symbol: str,
    period: str = "annual",
    limit: int = 10
) -> Dict[str, Any]:
    """
    Get financial growth metrics
    
    Args:
        symbol: Stock ticker symbol (e.g., 'AAPL', 'TSLA')
        period: 'annual' or 'quarter' (default 'annual')
        limit: Number of periods to return (default 10)
    """
    return await fmp_tools.get_financial_growth(symbol=symbol, period=period, limit=limit)


@tool(
    description=GET_QUOTE_DESC,
    category="financial_metrics"
)
async def get_quote(
    *,
    context: ToolContext,
    symbol: str
) -> Dict[str, Any]:
    """
    Get real-time stock quote
    
    Args:
        symbol: Stock ticker symbol (e.g., 'AAPL', 'TSLA')
    """
    return await fmp_tools.get_quote(symbol=symbol)


@tool(
    description=GET_HISTORICAL_PRICES_DESC,
    category="financial_metrics"
)
async def get_historical_prices(
    *,
    context: ToolContext,
    symbol: str,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    limit: int = 100
) -> Dict[str, Any]:
    """
    Get historical stock prices
    
    Args:
        symbol: Stock ticker symbol (e.g., 'AAPL', 'TSLA')
        from_date: Start date in YYYY-MM-DD format (optional)
        to_date: End date in YYYY-MM-DD format (optional)
        limit: Number of days to return (default 100)
    """
    return await fmp_tools.get_historical_prices(symbol=symbol, from_date=from_date, to_date=to_date, limit=limit)


@tool(
    description=GET_ANALYST_RECOMMENDATIONS_DESC,
    category="financial_metrics"
)
async def get_analyst_recommendations(
    *,
    context: ToolContext,
    symbol: str,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Get analyst recommendations
    
    Args:
        symbol: Stock ticker symbol (e.g., 'AAPL', 'TSLA')
        limit: Number of periods to return (default 10)
    """
    return await fmp_tools.get_analyst_recommendations(symbol=symbol, limit=limit)


@tool(
    description=SCREEN_STOCKS_DESC,
    category="financial_screening"
)
async def screen_stocks(
    *,
    context: ToolContext,
    market_cap_more_than: Optional[int] = None,
    market_cap_lower_than: Optional[int] = None,
    price_more_than: Optional[float] = None,
    price_lower_than: Optional[float] = None,
    sector: Optional[str] = None,
    industry: Optional[str] = None,
    country: Optional[str] = None,
    limit: int = 30
) -> Dict[str, Any]:
    """Screen stocks based on criteria"""
    return await fmp_tools.stock_screener(
        market_cap_more_than=market_cap_more_than,
        market_cap_lower_than=market_cap_lower_than,
        price_more_than=price_more_than,
        price_lower_than=price_lower_than,
        sector=sector,
        industry=industry,
        country=country,
        limit=limit
    )


@tool(
    description=GET_TOP_GAINERS_DESC,
    category="market_movers"
)
async def get_top_gainers(
    *,
    context: ToolContext
) -> Dict[str, Any]:
    """Get biggest stock gainers"""
    return await fmp_tools.get_market_gainers()


@tool(
    description=GET_TOP_LOSERS_DESC,
    category="market_movers"
)
async def get_top_losers(
    *,
    context: ToolContext
) -> Dict[str, Any]:
    """Get biggest stock losers"""
    return await fmp_tools.get_market_losers()


@tool(
    description=GET_MOST_ACTIVE_DESC,
    category="market_movers"
)
async def get_most_active_stocks(
    *,
    context: ToolContext
) -> Dict[str, Any]:
    """Get most actively traded stocks"""
    return await fmp_tools.get_most_active()


@tool(
    description=GET_SECTOR_PERFORMANCE_DESC,
    category="market_performance"
)
async def get_sectors_performance(
    *,
    context: ToolContext
) -> Dict[str, Any]:
    """Get sector performance"""
    return await fmp_tools.get_sector_performance()


@tool(
    description=GET_STOCK_NEWS_DESC,
    category="news"
)
async def get_stock_news_articles(
    *,
    context: ToolContext,
    symbols: Optional[List[str]] = None,
    limit: int = 20
) -> Dict[str, Any]:
    """Get stock news"""
    return await fmp_tools.get_stock_news(symbols=symbols, limit=limit)


@tool(
    description=GET_ETF_HOLDINGS_DESC,
    category="etf_data"
)
async def get_etf_holdings_data(
    *,
    context: ToolContext,
    symbol: str
) -> Dict[str, Any]:
    """Get ETF holdings"""
    return await fmp_tools.get_etf_holdings(symbol=symbol)


@tool(
    description=GET_ETF_INFO_DESC,
    category="etf_data"
)
async def get_etf_information(
    *,
    context: ToolContext,
    symbol: str
) -> Dict[str, Any]:
    """Get ETF information"""
    return await fmp_tools.get_etf_info(symbol=symbol)


@tool(
    description=GET_EARNINGS_CALENDAR_DESC,
    category="corporate_events"
)
async def get_earnings_schedule(
    *,
    context: ToolContext,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None
) -> Dict[str, Any]:
    """Get earnings calendar"""
    return await fmp_tools.get_earnings_calendar(from_date=from_date, to_date=to_date)


@tool(
    description=GET_DIVIDENDS_CALENDAR_DESC,
    category="corporate_events"
)
async def get_dividends_schedule(
    *,
    context: ToolContext,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None
) -> Dict[str, Any]:
    """Get dividends calendar"""
    return await fmp_tools.get_dividends_calendar(from_date=from_date, to_date=to_date)


@tool(
    description=GET_PRICE_TARGET_DESC,
    category="analyst_data"
)
async def get_analyst_price_targets(
    *,
    context: ToolContext,
    symbol: str
) -> Dict[str, Any]:
    """Get analyst price targets"""
    return await fmp_tools.get_price_target(symbol=symbol)


@tool(
    description=GET_UPGRADES_DOWNGRADES_DESC,
    category="analyst_data"
)
async def get_analyst_rating_changes(
    *,
    context: ToolContext,
    symbol: str,
    limit: int = 20
) -> Dict[str, Any]:
    """Get analyst upgrades and downgrades"""
    return await fmp_tools.get_upgrades_downgrades(symbol=symbol, limit=limit)


@tool(
    description=GET_PEER_COMPANIES_DESC,
    category="comparisons"
)
async def get_peer_companies(
    *,
    context: ToolContext,
    symbol: str
) -> Dict[str, Any]:
    """Get peer companies"""
    return await fmp_tools.get_stock_peers(symbol=symbol)


@tool(
    description=GET_ESG_SCORES_DESC,
    category="esg"
)
async def get_esg_scores(
    *,
    context: ToolContext,
    symbol: str
) -> Dict[str, Any]:
    """Get ESG scores"""
    return await fmp_tools.get_esg_score(symbol=symbol)


@tool(
    description=GET_SEC_FILINGS_DESC,
    category="sec_filings"
)
async def get_sec_filing_documents(
    *,
    context: ToolContext,
    symbol: Optional[str] = None,
    form_type: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    limit: int = 20
) -> Dict[str, Any]:
    """Get SEC filings"""
    return await fmp_tools.get_sec_filings(
        symbol=symbol,
        form_type=form_type,
        from_date=from_date,
        to_date=to_date,
        limit=limit
    )


# ============================================================================
# FINANCIAL ANALYSIS TOOLS (Financial Metrics Agent Delegation)
# ============================================================================

class AnalyzeFinancialsRequest(BaseModel):
    """Request parameters for financial analysis"""
    objective: str = Field(
        description="Detailed description of what to analyze. Examples: 'Analyze AAPL profitability trends', 'Compare TSLA vs F', 'Find tech stocks under $100', 'What are today's biggest gainers?', 'Analyze SPY ETF holdings'"
    )
    symbols: List[str] = Field(
        default_factory=list,
        description="List of stock ticker symbols to analyze (e.g., ['AAPL'], ['TSLA', 'F']). Can be empty for market screening/search tasks."
    )
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "objective": "Analyze Apple's profitability and cash generation over the past 5 years",
                    "symbols": ["AAPL"]
                },
                {
                    "objective": "Find technology stocks under $50 with market cap over $1B",
                    "symbols": []
                },
                {
                    "objective": "Show me today's biggest gainers and analyze why they're up",
                    "symbols": []
                }
            ]
        }


@tool(
    description=ANALYZE_FINANCIALS_DESC,
    category="financial_analysis"
)
async def analyze_financials(
    *,
    context: ToolContext,
    objective: str,
    symbols: List[str]
) -> Dict[str, Any]:
    """
    Analyze financial metrics and fundamentals for stocks using specialized FMP agent
    
    Args:
        objective: Detailed objective describing what to analyze (e.g., "Analyze Apple's profitability and compare to Microsoft", "Find growth stocks in tech sector")
        symbols: List of ticker symbols to analyze (can be empty for screening/search tasks)
    """
    try:
        import json
        
        # Build message for financial metrics agent
        symbols_str = ", ".join(symbols)
        user_message = f"Objective: {objective}\n\nSymbols to analyze: {symbols_str}"
        
        # Create agent context for financial metrics agent
        from modules.agent.context import AgentContext
        metrics_context = AgentContext(
            user_id=context.user_id,
            chat_id=context.chat_id,
            resource_manager=context.resource_manager
        )
        
        # Build messages using base class
        messages = financial_metrics_agent.build_messages(
            user_message,
            resource_manager=context.resource_manager
        )
        
        # Create LLM config for financial metrics agent
        from modules.agent.llm_config import LLMConfig
        llm_config = LLMConfig.from_config(
            model=financial_metrics_agent.get_model(),
            stream=False
        )
        
        # Run financial metrics agent's tool loop
        result = await financial_metrics_agent.run_tool_loop(
            initial_messages=messages,
            context=metrics_context,
            max_iterations=10,  # Allow multiple tool calls for comprehensive analysis
            llm_config=llm_config
        )
        
        if not result.get("success"):
            return {
                "success": False,
                "message": result.get("message", "Financial metrics agent failed")
            }
        
        # Return the agent's analysis
        return {
            "success": True,
            "objective": objective,
            "symbols": symbols,
            "analysis": result.get("content", ""),
            "tool_results": result.get("tool_results", []),
            "message": "Financial analysis complete. See 'analysis' field for detailed insights."
        }
    
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to analyze financials: {str(e)}"
        }


# ============================================================================
# VISUALIZATION TOOLS (Plotting Agent Delegation)
# ============================================================================

class CreatePlotRequest(BaseModel):
    """Request parameters for creating a plot"""
    objective: str = Field(
        description="Clear description of what to visualize. Examples: 'Create a line chart showing price trends', 'Compare these values with a bar chart', 'Show correlation with trendline'"
    )
    data: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional data to visualize. Can be raw data - the plotting agent will structure it appropriately. Can include arrays, objects, or structured data."
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "objective": "Create a line chart showing AAPL stock price with a linear trendline",
                "data": {
                    "dates": ["2024-01", "2024-02", "2024-03", "2024-04"],
                    "prices": [150, 155, 153, 160]
                }
            }
        }


@tool(
    description=CREATE_PLOT_DESC,
    category="visualization"
)
async def create_plot(
    *,
    context: ToolContext,
    objective: str,
    data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a plot by delegating to the specialized plotting agent
    
    Args:
        objective: What you want to visualize (e.g., "Show portfolio allocation as a pie chart")
        data: Optional data to visualize (the agent will structure it appropriately)
    """
    try:
        import json
        
        # Build message for plotting agent
        user_message = f"Objective: {objective}"
        if data:
            user_message += f"\n\nData provided:\n{json.dumps(data, indent=2)}"
        
        # Create agent context for plotting agent
        from modules.agent.context import AgentContext
        plotting_context = AgentContext(
            user_id=context.user_id,
            chat_id=context.chat_id,
            resource_manager=context.resource_manager
        )
        
        # Build messages using base class (resource_manager passed via kwargs)
        messages = plotting_agent.build_messages(
            user_message,
            resource_manager=context.resource_manager
        )
        
        # Create LLM config for plotting agent (GPT-5/o1 doesn't support custom temperature)
        from modules.agent.llm_config import LLMConfig
        llm_config = LLMConfig.from_config(
            model=plotting_agent.get_model(),
            stream=False
            # Note: temperature not set - o1 models only support default (1.0)
        )
        
        # Run plotting agent's tool loop (it will automatically call create_chart)
        result = await plotting_agent.run_tool_loop(
            initial_messages=messages,
            context=plotting_context,
            max_iterations=3,  # Plotting should be quick
            llm_config=llm_config
        )
        
        if not result.get("success"):
            return {
                "success": False,
                "message": result.get("message", "Plotting agent failed")
            }
        
        # Extract the plotting result from tool_results
        tool_results = result.get("tool_results", [])
        if tool_results:
            # Get the plot result from the plotting agent
            plot_result = tool_results[0]["result"]
            
            # Enhance the result with resource information
            if plot_result.get("success"):
                plot_result["resource_type"] = "plot"
                plot_result["message"] = f"{plot_result.get('message', '')}. This plot has been saved as a resource and can be viewed in the resources sidebar."
            
            return plot_result
        else:
            # Agent responded without calling tools
            return {
                "success": False,
                "message": f"Plotting agent couldn't create chart: {result.get('content', 'No response')}"
            }
    
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to create plot: {str(e)}"
        }


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
    
    # Financial metrics tools (FMP - Core)
    tool_registry.register_function(get_company_profile)
    tool_registry.register_function(get_income_statement)
    tool_registry.register_function(get_balance_sheet)
    tool_registry.register_function(get_cash_flow_statement)
    tool_registry.register_function(get_key_metrics)
    tool_registry.register_function(get_financial_ratios)
    tool_registry.register_function(get_financial_growth)
    tool_registry.register_function(get_quote)
    tool_registry.register_function(get_historical_prices)
    tool_registry.register_function(get_analyst_recommendations)
    
    # Financial screening & search
    tool_registry.register_function(screen_stocks)
    
    # Market movers & performance
    tool_registry.register_function(get_top_gainers)
    tool_registry.register_function(get_top_losers)
    tool_registry.register_function(get_most_active_stocks)
    tool_registry.register_function(get_sectors_performance)
    
    # News & press releases
    tool_registry.register_function(get_stock_news_articles)
    
    # ETF data
    tool_registry.register_function(get_etf_holdings_data)
    tool_registry.register_function(get_etf_information)
    
    # Corporate events
    tool_registry.register_function(get_earnings_schedule)
    tool_registry.register_function(get_dividends_schedule)
    
    # Analyst data (extended)
    tool_registry.register_function(get_analyst_price_targets)
    tool_registry.register_function(get_analyst_rating_changes)
    
    # Comparisons & peers
    tool_registry.register_function(get_peer_companies)
    
    # ESG
    tool_registry.register_function(get_esg_scores)
    
    # SEC filings
    tool_registry.register_function(get_sec_filing_documents)
    
    # Financial analysis tools (Financial Metrics Agent)
    tool_registry.register_function(analyze_financials)
    
    # Visualization tools (main agent)
    tool_registry.register_function(create_plot)
    
    # Low-level plotting tools (for plotting sub-agent)
    tool_registry.register_function(create_chart)


# Auto-register on import
register_all_tools()

