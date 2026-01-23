"""
Kalshi Markets APIs

Get events and market data from Kalshi prediction markets.
Requires user to have saved Kalshi API credentials.
"""
from typing import Dict, Any
import asyncio


def _run_with_client(async_func):
    """
    Run an async function with a fresh Kalshi client.
    
    Creates a new client and event loop for each call to avoid
    event loop closure issues. Properly closes client after use.
    """
    from ._client import create_client
    
    client = create_client()
    if not client:
        return {"error": "Kalshi credentials not found. Please add your Kalshi API key in Settings > API Keys."}
    
    async def wrapper():
        try:
            return await async_func(client)
        finally:
            await client.close()
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(wrapper())
    finally:
        loop.close()


def get_kalshi_events(limit: int = 20, status: str = "open") -> Dict[str, Any]:
    """
    Get Kalshi events (prediction market categories).
    
    Args:
        limit: Maximum number of events to return (default 20)
        status: Filter by status - "open", "closed", or "settled" (default "open")
        
    Returns:
        dict with:
        - events: List of event dicts with event_ticker, title, category, etc.
        - count: Number of events returned
        
    Example:
        events = get_kalshi_events(limit=10)
        if 'error' not in events:
            for event in events['events']:
                print(f"{event['event_ticker']}: {event['title']}")
    """
    async def fetch(client):
        result = await client.get_events(limit=limit, status=status)
        events = result.get("events", [])
        return {
            "events": events,
            "count": len(events)
        }
    
    try:
        return _run_with_client(fetch)
    except Exception as e:
        return {"error": f"Failed to get events: {str(e)}"}


def get_kalshi_market(ticker: str) -> Dict[str, Any]:
    """
    Get details for a specific Kalshi market.
    
    Args:
        ticker: The market ticker (e.g., "KXBTC-24DEC31-T100000")
        
    Returns:
        dict with market details including:
        - ticker: Market ticker
        - event_ticker: Parent event ticker
        - yes_bid/yes_ask: Current bid/ask for YES contracts (in cents)
        - no_bid/no_ask: Current bid/ask for NO contracts (in cents)
        - last_price: Last traded price (in cents)
        - volume: Trading volume
        - volume_24h: 24-hour trading volume
        - open_interest: Open interest
        - status: Market status
        
    Example:
        market = get_kalshi_market("KXBTC-24DEC31-T100000")
        if 'error' not in market:
            print(f"YES: {market['yes_bid']}¢ / {market['yes_ask']}¢")
    """
    async def fetch(client):
        return await client.get_market(ticker)
    
    try:
        return _run_with_client(fetch)
    except Exception as e:
        return {"error": f"Failed to get market: {str(e)}"}
