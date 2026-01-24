"""
Kalshi Markets - Search and Pricing

Access Kalshi prediction markets via Dome API (read-only).
"""
from typing import Optional, Literal, Dict, Any
from .._client import call_dome_api


def get_markets(
    series_ticker: Optional[str] = None,
    status: Optional[Literal["active", "settled", "closed"]] = None,
    limit: int = 10,
    offset: int = 0
) -> Dict[str, Any]:
    """
    Search Kalshi prediction markets.
    
    Args:
        series_ticker: Filter by series ticker (e.g., 'FED' for Federal Reserve)
        status: Filter by status - 'active', 'settled', or 'closed'
        limit: Number of markets to return (1-100, default 10)
        offset: Number to skip for pagination (default 0)
        
    Returns:
        dict with:
        - markets: List of markets with:
            - ticker: Market ticker (e.g., 'FED-24FEB28-T4.75')
            - title: Market question
            - series_ticker: Parent series
            - status: active/settled/closed
            - strike_price: Strike price (if applicable)
            - expiration_time: Expiration timestamp
            - volume: Trading volume
            - open_interest: Open interest
            - yes_bid/yes_ask: Current bid/ask prices (cents)
        - pagination: Pagination info
        
    Example:
        # Get active Fed rate markets
        markets = get_markets(series_ticker='FED', status='active')
        if 'error' not in markets:
            for m in markets['markets']:
                print(f"{m['ticker']}: {m['title']}")
                print(f"  YES: {m['yes_bid']}¢ / {m['yes_ask']}¢")
    """
    params = {
        "limit": min(max(1, limit), 100),
        "offset": max(0, offset)
    }
    
    if series_ticker:
        params["series_ticker"] = series_ticker
    if status:
        params["status"] = status
    
    return call_dome_api("/kalshi/markets", params)


def get_market_price(
    ticker: str,
    at_time: Optional[int] = None
) -> Dict[str, Any]:
    """
    Get current or historical price for a Kalshi market.
    
    Args:
        ticker: Market ticker (e.g., 'FED-24FEB28-T4.75')
        at_time: Optional Unix timestamp (seconds) for historical price
                 If not provided, returns most recent price
        
    Returns:
        dict with:
        - price: Market price in cents, 0-100 (e.g., 65 = 65¢ = 65%)
        - at_time: Unix timestamp for the price
        
    Example:
        # Get current price
        price = get_market_price("FED-24FEB28-T4.75")
        if 'error' not in price:
            print(f"Current price: {price['price']}¢ ({price['price']}% probability)")
    """
    endpoint = f"/kalshi/market-price/{ticker}"
    params = {}
    
    if at_time:
        params["at_time"] = at_time
    
    return call_dome_api(endpoint, params)
