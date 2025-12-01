"""
Central tool definitions file
All LLM-callable tools are defined here using the @tool decorator
"""
import json
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from modules.tools import tool, tool_registry
from modules.agent.context import AgentContext
from models.sse import OptionButton, SSEEvent

# Import business logic modules (API clients)
from modules.tools.clients.snaptrade import snaptrade_tools
from modules.tools.clients.apewisdom import apewisdom_tools
from modules.tools.clients.fmp import fmp_tools  # Universal FMP tool (includes insider trading)
from modules.tools.clients.plotting import create_chart

# Import V2 strategy tools (new LLM-native framework)
# Tools are registered via @tool decorator on import
import modules.tools.strategy_tools_v2  # noqa: F401

# Import code-based strategy tools (code generation approach)
import modules.tools.strategy_code_tools  # noqa: F401

# Import financial code execution (Manus-style data analysis)
import modules.tools.financial_code_tools  # noqa: F401

# Import file tools (Manus-style file operations)
import modules.tools.file_tools  # noqa: F401

# Import tool descriptions
from modules.tools.descriptions import (
    # Portfolio
    GET_PORTFOLIO_DESC, REQUEST_BROKERAGE_CONNECTION_DESC,
    # Reddit sentiment
    GET_REDDIT_TRENDING_DESC, GET_REDDIT_TICKER_SENTIMENT_DESC, COMPARE_REDDIT_SENTIMENT_DESC,
    # Financial metrics (FMP - Universal tool including insider trading)
    GET_FMP_DATA_DESC
)


# ============================================================================
# PORTFOLIO TOOLS (SnapTrade)
# ============================================================================

@tool(
    description=GET_PORTFOLIO_DESC,
    category="portfolio",
    requires_auth=True
)
async def get_portfolio(
    *,
    context: AgentContext
):
    """Get user's portfolio holdings"""
    if not context.user_id:
        yield {
            "success": False,
            "message": "User ID required",
            "needs_auth": True
        }
        return
    
    # Call client which will yield SSE events and then result
    async for item in snaptrade_tools.get_portfolio_streaming(
        user_id=context.user_id
    ):
        yield item


@tool(
    description=REQUEST_BROKERAGE_CONNECTION_DESC,
    category="portfolio",
    requires_auth=False
)
def request_brokerage_connection(
    *,
    context: AgentContext
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
    context: AgentContext,
    limit: int = 10
):
    """
    Get trending stocks from Reddit communities
    
    Args:
        limit: Number of trending stocks to return (default 10, max 50)
    """
    # Yield status event
    yield SSEEvent(
        event="tool_status",
        data={
            "status": "fetching",
            "message": f"Scanning r/wallstreetbets for top {limit} trending stocks..."
        }
    )
    
    result = await apewisdom_tools.get_trending_stocks(limit=limit)
    
    if result.get("success"):
        mentions = result.get("data", {}).get("mentions", [])
        # Yield log event
        yield SSEEvent(
            event="tool_log",
            data={
                "level": "info",
                "message": f"Found {len(mentions)} trending stocks"
            }
        )
    
    # Yield final result
    yield result


@tool(
    description=GET_REDDIT_TICKER_SENTIMENT_DESC,
    category="reddit_sentiment"
)
async def get_reddit_ticker_sentiment(
    *,
    context: AgentContext,
    ticker: str
):
    """
    Get Reddit sentiment for a specific stock ticker
    
    Args:
        ticker: Stock ticker symbol (e.g., 'GME', 'TSLA', 'AAPL')
    """
    yield SSEEvent(
        event="tool_status",
        data={
            "status": "analyzing",
            "message": f"Analyzing Reddit sentiment for ${ticker.upper()} from r/wallstreetbets..."
        }
    )
    
    result = await apewisdom_tools.get_ticker_sentiment(ticker=ticker)
    
    if result.get("success"):
        data = result.get("data", {})
        mentions = data.get("mentions", 0)
        yield SSEEvent(
            event="tool_log",
            data={
                "level": "info",
                "message": f"Found {mentions} Reddit mentions"
            }
        )
    
    yield result


@tool(
    description=COMPARE_REDDIT_SENTIMENT_DESC,
    category="reddit_sentiment"
)
async def compare_reddit_sentiment(
    *,
    context: AgentContext,
    tickers: List[str]
):
    """
    Compare Reddit sentiment for multiple tickers
    
    Args:
        tickers: List of ticker symbols to compare (e.g., ['GME', 'AMC', 'TSLA'])
    """
    tickers_str = ", ".join([t.upper() for t in tickers])
    yield SSEEvent(
        event="tool_status",
        data={
            "status": "analyzing",
            "message": f"Comparing Reddit sentiment: {tickers_str}"
        }
    )
    
    result = await apewisdom_tools.compare_tickers_sentiment(tickers=tickers)
    
    if result.get("success"):
        yield SSEEvent(
            event="tool_log",
            data={
                "level": "info",
                "message": f"Compared {len(tickers)} tickers"
            }
        )
    
    yield result


# ============================================================================
# FINANCIAL METRICS TOOLS (Financial Modeling Prep)
# Universal tool for ALL FMP data including insider trading
# ============================================================================

@tool(
    description=GET_FMP_DATA_DESC,
    category="financial_metrics"
)
async def get_fmp_data(
    *,
    context: AgentContext,
    endpoint: str,
    params: Optional[Dict[str, Any]] = None
):
    """Universal tool to fetch ANY financial data from FMP API including insider trading. See description for available endpoints."""
    # Handle case where params might be passed as a JSON string
    if isinstance(params, str):
        try:
            params = json.loads(params)
        except json.JSONDecodeError:
            params = {}
    
    # Emit initial status with readable endpoint name and specific parameters
    endpoint_name = endpoint.replace('_', ' ').replace('-', ' ').title()
    symbol_str = params.get('symbol', '') if params else ''
    
    if symbol_str:
        yield SSEEvent(
            event="tool_status",
            data={
                "status": "executing",
                "message": f"Starting {endpoint_name} fetch for {symbol_str}..."
            }
        )
    else:
        yield SSEEvent(
            event="tool_status",
            data={
                "status": "executing",
                "message": f"Starting {endpoint_name} data fetch..."
            }
        )
    
    # Call FMP client - it will also yield SSE events  
    async for item in fmp_tools.get_fmp_data_streaming(
        endpoint=endpoint, 
        params=params or {}
    ):
        if isinstance(item, SSEEvent):
            yield item
        else:
            result = item
    
    # Emit final status based on result
    if result.get("success"):
        count = result.get("count", 0)
        if count > 0:
            yield SSEEvent(
                event="tool_status",
                data={
                    "status": "completed",
                    "message": f"✓ Retrieved {count} {endpoint_name.lower()} records"
                }
            )
        else:
            yield SSEEvent(
                event="tool_status",
                data={
                    "status": "completed",
                    "message": f"✓ {endpoint_name} data retrieved successfully"
                }
            )
    else:
        error_msg = result.get("message", "Unknown error")
        yield SSEEvent(
            event="tool_status",
            data={
                "status": "error",
                "message": f"✗ {error_msg}"
            }
        )
    
    yield result


# ============================================================================
# INTERACTIVE OPTIONS TOOL
# ============================================================================

class PresentOptionsInput(BaseModel):
    """Input model for present_options tool"""
    question: str = Field(
        ...,
        description="The question to ask the user (shown above the option buttons)"
    )
    options: List[OptionButton] = Field(
        ...,
        description="List of option buttons to present (2-6 options)",
        min_length=2,
        max_length=6
    )


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
async def present_options(
    *,
    context: AgentContext,
    params: PresentOptionsInput
):
    """
    Present option buttons to the user
    
    Args:
        params: PresentOptionsInput containing question and option buttons
    """
    # Yield options event
    yield SSEEvent(
        event="tool_options",
        data={
        "question": params.question,
        "options": [opt.model_dump() for opt in params.options]
        }
    )
    
    # Yield final result indicating options were presented
    # The conversation should pause here waiting for user selection
    yield {
        "success": True,
        "message": "Options presented to user. Waiting for user selection.",
        "question": params.question,
        "options": [opt.model_dump() for opt in params.options],
        "_stop_response": True  # Signal that response should end after this
    }


# ============================================================================
# ANALYTICS TOOLS (Transaction History & Performance)
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
async def get_transaction_history(
    *,
    context: AgentContext,
    symbol: Optional[str] = None,
    limit: int = 100
):
    """Fetch user's transaction history"""
    from services.transaction_sync import transaction_sync_service
    from crud import transactions as tx_crud
    from database import SessionLocal
    
    if not context.user_id:
        yield {
            "success": False,
            "message": "User ID required",
            "needs_auth": True
        }
        return
    
    # First, sync transactions from SnapTrade
    yield SSEEvent(
        event="tool_status",
        data={
            "status": "syncing",
            "message": "Syncing your latest transactions from brokerage..."
        }
    )
    
    sync_result = await transaction_sync_service.sync_user_transactions(context.user_id)
    
    if not sync_result.get("success"):
        yield {
            "success": False,
            "message": sync_result.get("message", "Failed to sync transactions")
        }
        return
    
    # Now fetch transactions from DB
    db = SessionLocal()
    try:
        transactions = tx_crud.get_transactions(
            db,
            user_id=context.user_id,
            symbol=symbol,
            limit=min(limit, 500)
        )
        
        # Format transactions for display
        formatted = []
        for tx in transactions:
            formatted.append({
                "id": str(tx.id),
                "symbol": tx.symbol,
                "type": tx.transaction_type,
                "date": tx.transaction_date.isoformat(),
                "quantity": float(tx.data.get("quantity", 0)),
                "price": float(tx.data.get("price")) if tx.data.get("price") else None,
                "total": float(tx.data.get("total_amount", 0)),
                "description": tx.data.get("description", "")
            })
        
        yield {
            "success": True,
            "data": {
                "transactions": formatted,
                "total_count": len(formatted),
                "synced": sync_result.get("transactions_inserted", 0) + sync_result.get("transactions_updated", 0)
            },
            "message": f"Found {len(formatted)} transactions" + (f" for {symbol}" if symbol else "")
        }
        
    finally:
        db.close()


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
async def analyze_portfolio_performance(
    *,
    context: AgentContext,
    period: str = "all_time"
):
    """Analyze overall portfolio performance"""
    from services.analytics import analytics_service
    from services.transaction_sync import transaction_sync_service
    
    if not context.user_id:
        yield {
            "success": False,
            "message": "User ID required",
            "needs_auth": True
        }
        return
    
    # Sync transactions first (with background sync)
    yield SSEEvent(
        event="tool_status",
        data={
            "status": "syncing",
            "message": "Checking for latest transactions..."
        }
    )
    
    sync_result = await transaction_sync_service.sync_user_transactions(
        context.user_id,
        background_sync=True  # Enable background sync
    )
    
    # Calculate performance metrics
    yield SSEEvent(
        event="tool_status",
        data={
            "status": "analyzing",
            "message": f"Analyzing your trading performance ({period})..."
        }
    )
    
    metrics = analytics_service.calculate_performance_metrics(
        context.user_id,
        period=period
    )
    
    # Build staleness message
    staleness_msg = ""
    if sync_result.get("cached") and sync_result.get("staleness_seconds"):
        staleness_seconds = sync_result["staleness_seconds"]
        if staleness_seconds < 60:
            staleness_msg = f" (data from {staleness_seconds}s ago)"
        elif staleness_seconds < 3600:
            staleness_msg = f" (data from {staleness_seconds // 60}m ago)"
        else:
            staleness_msg = f" (data from {staleness_seconds // 3600}h ago)"
        
        if sync_result.get("background_sync"):
            staleness_msg += " - updating in background"
    
    if metrics.get("total_trades", 0) == 0:
        yield {
            "success": True,
            "data": metrics,
            "message": f"No closed trades found in this period{staleness_msg}. Connect your brokerage and make some trades to see analytics!",
            "data_staleness_seconds": sync_result.get("staleness_seconds"),
            "background_sync": sync_result.get("background_sync", False)
        }
        return
    
    yield {
        "success": True,
        "data": metrics,
        "message": f"Performance analysis complete for {period}{staleness_msg}. You've made {metrics['total_trades']} trades with a {metrics['win_rate']:.1f}% win rate!",
        "data_staleness_seconds": sync_result.get("staleness_seconds"),
        "background_sync": sync_result.get("background_sync", False)
    }


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
async def identify_trading_patterns(
    *,
    context: AgentContext
):
    """Identify behavioral trading patterns"""
    from services.analytics import analytics_service
    from services.transaction_sync import transaction_sync_service
    
    if not context.user_id:
        yield {
            "success": False,
            "message": "User ID required",
            "needs_auth": True
        }
        return
    
    # Sync first (with background sync)
    yield SSEEvent(
        event="tool_status",
        data={
            "status": "analyzing",
            "message": "Analyzing your trading patterns..."
        }
    )
    
    sync_result = await transaction_sync_service.sync_user_transactions(
        context.user_id,
        background_sync=True
    )
    
    patterns = analytics_service.analyze_trading_patterns(context.user_id)
    
    # Build staleness message
    staleness_msg = ""
    if sync_result.get("cached") and sync_result.get("staleness_seconds"):
        staleness_seconds = sync_result["staleness_seconds"]
        if staleness_seconds < 60:
            staleness_msg = f" (data from {staleness_seconds}s ago)"
        elif staleness_seconds < 3600:
            staleness_msg = f" (data from {staleness_seconds // 60}m ago)"
        else:
            staleness_msg = f" (data from {staleness_seconds // 3600}h ago)"
    
    if not patterns:
        yield {
            "success": True,
            "data": {"patterns": []},
            "message": f"Not enough trading history to detect patterns yet{staleness_msg}. Keep trading and check back after 10+ closed positions!",
            "data_staleness_seconds": sync_result.get("staleness_seconds"),
            "background_sync": sync_result.get("background_sync", False)
        }
        return
    
    yield {
        "success": True,
        "data": {"patterns": patterns},
        "message": f"Found {len(patterns)} trading patterns to review{staleness_msg}",
        "data_staleness_seconds": sync_result.get("staleness_seconds"),
        "background_sync": sync_result.get("background_sync", False)
    }


# ============================================================================
# ============================================================================
# TRADING STRATEGY TOOLS - V2 (Modern LLM-Native Framework)
# ============================================================================
# Strategy tools moved to modules/tools/strategy_tools_v2.py
# New LLM-native approach where strategies are natural language rules
#
# Available V2 tools (auto-imported):
# - create_trading_strategy: Create rule-based strategies  
# - test_strategy: Test on a single ticker
# - scan_with_strategy: Scan multiple tickers
# - list_strategies: List all strategies
# - get_strategy_details: Get strategy details
# - delete_strategy: Delete a strategy
# ============================================================================

# ============================================================================
# AUTO-REGISTRATION
# ============================================================================
# Tools are now AUTO-REGISTERED when the @tool decorator is applied!
# No manual registration needed - just import the modules and tools register themselves.
#
# The agent_config.py controls which tools each agent can use (policy layer).
# This file just imports all tool modules to trigger registration.

# Import V2 strategy tools (auto-registers on import)
import modules.tools.strategy_tools_v2
# Import code-based strategy tools (auto-registers on import)
import modules.tools.strategy_code_tools  # noqa: F401

# All tools in this file are auto-registered when @tool decorator runs
# Total tools: 17 (11 in this file + 6 from strategy_tools_v2)

