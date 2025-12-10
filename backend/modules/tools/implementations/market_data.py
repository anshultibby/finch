"""
Market data tool implementations - Reddit sentiment, FMP, Polygon
"""
import json
from typing import Dict, Any, List, Optional, AsyncGenerator
from modules.agent.context import AgentContext
from models.sse import SSEEvent
from modules.tools.clients.apewisdom import apewisdom_tools


async def get_reddit_trending_stocks_impl(
    context: AgentContext,
    limit: int = 10
) -> AsyncGenerator:
    """Get trending stocks from Reddit communities"""
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
        yield SSEEvent(
            event="tool_log",
            data={
                "level": "info",
                "message": f"Found {len(mentions)} trending stocks"
            }
        )
    
    yield result


async def get_reddit_ticker_sentiment_impl(
    context: AgentContext,
    ticker: str
) -> AsyncGenerator:
    """Get Reddit sentiment for a specific stock ticker"""
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


async def compare_reddit_sentiment_impl(
    context: AgentContext,
    tickers: List[str]
) -> AsyncGenerator:
    """Compare Reddit sentiment for multiple tickers"""
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


async def get_fmp_data_impl(
    context: AgentContext,
    endpoint: str,
    params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """FMP API documentation (generated as markdown file in /apis/)"""
    return {
        "success": True,
        "message": "FMP API documentation available in /apis/get_fmp_data.md"
    }


async def polygon_api_docs_impl(context: AgentContext) -> Dict[str, Any]:
    """Polygon.io API documentation (generated as markdown file in /apis/)"""
    return {
        "success": True,
        "message": "Polygon.io API documentation available"
    }

