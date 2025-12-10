"""
Central tool definitions file - Registry only
All LLM-callable tools are defined here using the @tool decorator.
Implementations are in modules/tools/implementations/
"""
from typing import Dict, Any, List, Optional
from modules.tools import tool
from modules.agent.context import AgentContext

# Import tool descriptions
from modules.tools.descriptions import (
    GET_PORTFOLIO_DESC, REQUEST_BROKERAGE_CONNECTION_DESC,
    GET_REDDIT_TRENDING_DESC, GET_REDDIT_TICKER_SENTIMENT_DESC, COMPARE_REDDIT_SENTIMENT_DESC,
    GET_FMP_DATA_DESC
)

# Import implementations
from modules.tools.implementations import planning, portfolio, market_data, analytics
from modules.tools.implementations import interactive, web, control
from modules.tools.implementations.code_execution import execute_code
from modules.tools.implementations.file_management import (
    list_chat_files, write_chat_file, read_chat_file, 
    replace_in_chat_file, find_in_chat_file
)
from modules.tools.implementations.etf_builder import build_custom_etf
from modules.tools.clients.plotting import create_chart


# ============================================================================
# PLANNING TOOLS
# ============================================================================

@tool(
    description="Create or replace a structured plan for complex multi-step tasks. Use this to organize work into clear phases. Creating a new plan replaces any existing plan.",
    category="planning"
)
def create_plan(*, context: AgentContext, goal: str, phases: List[dict]):
    """Create a structured plan for complex tasks"""
    return planning.create_plan_impl(context, goal, phases)


@tool(
    description="Advance to the next phase in your current plan. Call this when you've completed the current phase and are ready to move to the next one.",
    category="planning"
)
def advance_plan(*, context: AgentContext):
    """Advance to the next phase in the plan"""
    return planning.advance_plan_impl(context)


# ============================================================================
# PORTFOLIO & BROKERAGE TOOLS
# ============================================================================

@tool(
    description=GET_PORTFOLIO_DESC,
    category="portfolio",
    requires_auth=True
)
async def get_portfolio(*, context: AgentContext):
    """Get user's portfolio holdings"""
    async for item in portfolio.get_portfolio_impl(context):
        yield item


@tool(
    description=REQUEST_BROKERAGE_CONNECTION_DESC,
    category="portfolio",
    requires_auth=False
)
def request_brokerage_connection(*, context: AgentContext) -> Dict[str, Any]:
    """Request user to connect their brokerage account"""
    return portfolio.request_brokerage_connection_impl(context)


# ============================================================================
# MARKET DATA TOOLS
# ============================================================================

@tool(
    description=GET_REDDIT_TRENDING_DESC,
    category="reddit_sentiment",
    api_docs_only=True
)
async def get_reddit_trending_stocks(*, context: AgentContext, limit: int = 10):
    """Get trending stocks from Reddit communities"""
    async for item in market_data.get_reddit_trending_stocks_impl(context, limit):
        yield item


@tool(
    description=GET_REDDIT_TICKER_SENTIMENT_DESC,
    category="reddit_sentiment",
    api_docs_only=True
)
async def get_reddit_ticker_sentiment(*, context: AgentContext, ticker: str):
    """Get Reddit sentiment for a specific stock ticker"""
    async for item in market_data.get_reddit_ticker_sentiment_impl(context, ticker):
        yield item


@tool(
    description=COMPARE_REDDIT_SENTIMENT_DESC,
    category="reddit_sentiment",
    api_docs_only=True
)
async def compare_reddit_sentiment(*, context: AgentContext, tickers: List[str]):
    """Compare Reddit sentiment for multiple tickers"""
    async for item in market_data.compare_reddit_sentiment_impl(context, tickers):
        yield item


@tool(
    description=GET_FMP_DATA_DESC,
    category="financial_metrics",
    api_docs_only=True
)
async def get_fmp_data(*, context: AgentContext, endpoint: str, params: Optional[Dict[str, Any]] = None):
    """Universal tool to fetch ANY financial data from FMP API"""
    async for item in market_data.get_fmp_data_impl(context, endpoint, params):
        yield item


@tool(
    description="""Polygon.io REST API - Real-time and historical market data

**Workflow for Using Polygon API:**
1. Use `fetch_webpage` tool to get documentation: https://polygon.readthedocs.io/en/latest/Stocks.html
2. Parse the HTML/text to find endpoint patterns and parameters
3. Write Python code using `polygon.get_aggs()` and other methods
4. Execute the code with `execute_code` tool

**Usage in Code:**
```python
from finch_runtime import polygon

# Use the official Polygon Python client methods
aggs = polygon.get_aggs('AAPL', 1, 'day', '2024-01-01', '2024-12-31')
snapshot = polygon.get_snapshot_ticker('stocks', 'AAPL')
details = polygon.get_ticker_details('AAPL')
tickers = polygon.list_tickers(search='Apple', limit=10)
```

**Base URL:** https://api.polygon.io
**API Key:** Automatically added by polygon client

**Documentation URLs:**
- Full API docs: https://polygon.readthedocs.io/en/latest/Stocks.html
- REST API reference: https://polygon.io/docs/stocks/getting-started

**Common Methods:**
- get_aggs(ticker, multiplier, timespan, from_, to): Get aggregate bars
- get_snapshot_ticker(ticker_type, ticker): Get current snapshot
- get_ticker_details(ticker): Get ticker details
- list_tickers(search=None, market='stocks'): Search tickers
- get_previous_close_agg(ticker): Get previous close
- get_grouped_daily_aggs(date): Get all stocks for a date""",
    category="market_data",
    api_docs_only=True
)
async def polygon_api_docs(*, context: AgentContext):
    """Polygon.io API documentation (generated as markdown file in /apis/)"""
    return await market_data.polygon_api_docs_impl(context)


# ============================================================================
# WEB CONTENT TOOLS
# ============================================================================

@tool(
    description="Fetch and read content from any web URL. Useful for reading API documentation, articles, or any web content.",
    category="web"
)
async def fetch_webpage(*, context: AgentContext, url: str, extract_text: bool = False) -> Dict[str, Any]:
    """Fetch content from a web URL"""
    return await web.fetch_webpage_impl(context, url, extract_text)


# ============================================================================
# ANALYTICS TOOLS
# ============================================================================

@tool(
    description="""Sync and retrieve the user's complete transaction history from their connected brokerage.
    This fetches all stock trades (buys, sells), dividends, and fees for analysis.
    
    Use this when the user asks about:
    - Past trades or transaction history
    - "What stocks have I traded?"
    - "Show me my transactions"
    - Before analyzing performance (to ensure data is up-to-date)
    
    Parameters:
    - symbol: Optional ticker to filter (e.g., 'AAPL')
    - limit: Max transactions to return (default 100, max 500)
    """,
    category="analytics",
    requires_auth=True
)
async def get_transaction_history(*, context: AgentContext, symbol: Optional[str] = None, limit: int = 100):
    """Fetch user's transaction history"""
    async for item in analytics.get_transaction_history_impl(context, symbol, limit):
        yield item


@tool(
    description="""Analyze the user's overall portfolio performance including win rate, P&L, best/worst trades,
    and behavioral patterns. This provides a comprehensive performance report.
    
    Use this when the user asks:
    - "How am I doing?"
    - "Analyze my performance"
    - "What's my win rate?"
    - "Show me my trading stats"
    - "Am I a good trader?"
    
    Parameters:
    - period: Time period to analyze (all_time, ytd, 1m, 3m, 6m, 1y)
    """,
    category="analytics",
    requires_auth=True
)
async def analyze_portfolio_performance(*, context: AgentContext, period: str = "all_time"):
    """Analyze overall portfolio performance"""
    async for item in analytics.analyze_portfolio_performance_impl(context, period):
        yield item


@tool(
    description="""Identify behavioral patterns in the user's trading such as:
    - Early exit on winners / Holding losers too long
    - Overtrading
    - Risk/reward imbalance
    - High/low win rate tendencies
    
    Use this when the user asks:
    - "What patterns do you see in my trading?"
    - "What am I doing wrong?"
    - "How can I improve?"
    - "What are my bad habits?"
    """,
    category="analytics",
    requires_auth=True
)
async def identify_trading_patterns(*, context: AgentContext):
    """Identify behavioral trading patterns"""
    async for item in analytics.identify_trading_patterns_impl(context):
        yield item


# ============================================================================
# INTERACTIVE TOOLS
# ============================================================================

@tool(
    description="""Present interactive option buttons to the user for them to choose from.

Use this when you want to guide the user through a workflow with specific choices rather than open-ended questions.

Examples:
- Investment timeframes (short/medium/long term)
- Analysis depth (quick/standard/deep)
- Portfolio actions (review/opportunities/trim)
- Stock screening criteria (growth/value/dividend)

The user will select one option, and their selection will be returned as the next message.
You should then acknowledge their choice and proceed with the appropriate action.

This provides better UX than asking open-ended questions for well-defined workflows.

IMPORTANT: Do NOT generate any follow-up text after calling this tool. The conversation will pause to wait for user selection.""",
    category="interaction"
)
async def present_options(*, context: AgentContext, params: interactive.PresentOptionsInput):
    """Present option buttons to the user"""
    async for item in interactive.present_options_impl(context, params):
        yield item


# ============================================================================
# CONTROL TOOLS
# ============================================================================

@tool(
    description="""Signal that you have completed all tasks and are ready for the user's next input.
    
    Use this tool when:
    - You have finished answering the user's question
    - You have completed all requested tasks
    - You are waiting for additional user input or clarification
    - You have nothing more to add to the current conversation
    
    This helps the interface know when to return to an input-ready state.
    
    Do NOT use this tool if:
    - You are still processing information
    - You are waiting for tool results
    - You have more analysis or information to provide
    """,
    category="control",
    hidden_from_ui=True
)
def idle(*, context: AgentContext) -> Dict[str, Any]:
    """Signal completion and return to idle state"""
    return control.idle_impl(context)


# ============================================================================
# IMPORTED TOOLS (already have @tool decorator in their modules)
# ============================================================================
# These tools are defined and decorated in their respective modules:
# - execute_code (from implementations/code_execution.py)
# - list_chat_files, write_chat_file, read_chat_file, replace_in_chat_file, find_in_chat_file (from implementations/file_management.py)
# - build_custom_etf (from implementations/etf_builder.py)
# - create_chart (from clients/plotting.py)

# Import them so they register with the tool registry
__all__ = [
    # Planning
    'create_plan', 'advance_plan',
    # Portfolio
    'get_portfolio', 'request_brokerage_connection',
    # Market Data
    'get_reddit_trending_stocks', 'get_reddit_ticker_sentiment', 'compare_reddit_sentiment',
    'get_fmp_data', 'polygon_api_docs',
    # Web
    'fetch_webpage',
    # Analytics
    'get_transaction_history', 'analyze_portfolio_performance', 'identify_trading_patterns',
    # Interactive
    'present_options',
    # Control
    'idle',
    # Imported (already decorated)
    'execute_code', 'list_chat_files', 'write_chat_file', 'read_chat_file', 
    'replace_in_chat_file', 'find_in_chat_file', 'build_custom_etf', 'create_chart'
]

