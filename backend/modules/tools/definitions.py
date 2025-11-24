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
    
    # Financial metrics tools (FMP - Universal tool including insider trading)
    tool_registry.register_function(get_fmp_data)
    
    # Visualization tools
    tool_registry.register_function(create_chart)
    
    # Interactive options tool
    tool_registry.register_function(present_options)


# Auto-register on import
register_all_tools()

