"""
Polymarket Trading - Trade Execution History via Dome API

Get actual BUY/SELL trade executions from Polymarket via Dome's /polymarket/orders endpoint.
This provides real execution data including prices, shares, and wallet addresses.
"""
from typing import Optional, Dict, Any
from .._client import call_dome_api


def get_orders(
    user: Optional[str] = None,
    condition_id: Optional[str] = None,
    market_slug: Optional[str] = None,
    token_id: Optional[str] = None,
    start_time: Optional[int] = None,
    end_time: Optional[int] = None,
    limit: int = 100,
    pagination_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get executed orders (actual BUY/SELL trades) from Polymarket.
    
    This is the primary endpoint for fetching real trade execution data.
    Returns filled orders with price, shares, and transaction details.
    
    Args:
        user: Filter by wallet address (to get a specific trader's executions)
        condition_id: Filter by condition ID (specific market)
        market_slug: Filter by market slug
        token_id: Filter by token ID (specific outcome - Yes/No)
        start_time: Unix timestamp (seconds) filter from (inclusive)
        end_time: Unix timestamp (seconds) filter until (inclusive)
        limit: Number of orders to return (1-1000, default 100)
        pagination_key: Cursor for pagination (from previous response)
        
    Returns:
        dict with:
        - orders: List of executed orders with:
            - token_id: Token ID
            - token_label: 'Yes' or 'No'
            - side: 'BUY' or 'SELL'
            - market_slug: Market identifier
            - condition_id: Condition ID
            - shares: Raw shares (use shares_normalized instead)
            - shares_normalized: Normalized share amount
            - price: Execution price (0-1, e.g., 0.65 = 65 cents)
            - block_number: Blockchain block number
            - tx_hash: Transaction hash
            - title: Market title
            - timestamp: Unix timestamp of execution
            - order_hash: Order identifier
            - user: Maker wallet address
            - taker: Taker wallet address
        - pagination: Pagination info with limit, offset, total, has_more, pagination_key
        
    Example:
        # Get a wallet's recent trade executions
        orders = get_orders(user="0x6a72f61820b26b1fe4d956e17b6dc2a1ea3033ee", limit=100)
        if 'error' not in orders:
            for order in orders['orders']:
                print(f"{order['side']} {order['shares_normalized']:.2f} shares "
                      f"@ ${order['price']:.2f} - {order['title']}")
        
        # Get trades for a specific market
        orders = get_orders(market_slug="bitcoin-above-100000", limit=50)
    """
    params = {"limit": min(max(1, limit), 1000)}
    
    if user:
        params["user"] = user
    if condition_id:
        params["condition_id"] = condition_id
    if market_slug:
        params["market_slug"] = market_slug
    if token_id:
        params["token_id"] = token_id
    if start_time:
        params["start_time"] = start_time
    if end_time:
        params["end_time"] = end_time
    if pagination_key:
        params["pagination_key"] = pagination_key
    
    return call_dome_api("/polymarket/orders", params)


def get_trade_history(
    condition_id: Optional[str] = None,
    market_slug: Optional[str] = None,
    token_id: Optional[str] = None,
    user: Optional[str] = None,
    start_time: Optional[int] = None,
    end_time: Optional[int] = None,
    limit: int = 100,
    pagination_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Alias for get_orders() - Get executed trades from Polymarket.
    
    DEPRECATED: Use get_orders() instead for clarity.
    This function is kept for backward compatibility.
    
    See get_orders() for full documentation.
    """
    return get_orders(
        user=user,
        condition_id=condition_id,
        market_slug=market_slug,
        token_id=token_id,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        pagination_key=pagination_key
    )
