"""
Kalshi Trading APIs

Place orders, view orders, and cancel orders on Kalshi prediction markets.
Requires user to have saved Kalshi API credentials.
"""
from typing import Dict, Any, Optional
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


def place_kalshi_order(
    ticker: str,
    side: str,
    action: str,
    count: int,
    order_type: str = "market",
    price: Optional[int] = None
) -> Dict[str, Any]:
    """
    Place an order on Kalshi.
    
    Args:
        ticker: Market ticker (e.g., "KXBTC-24DEC31-T100000")
        side: "yes" or "no" - which side of the market to trade
        action: "buy" or "sell"
        count: Number of contracts to trade
        order_type: "market" or "limit" (default "market")
        price: Limit price in cents (required for limit orders, 1-99)
        
    Returns:
        dict with:
        - order_id: Unique order ID
        - ticker: Market ticker
        - status: Order status
        - side: "yes" or "no"
        - action: "buy" or "sell"
        - count: Number of contracts
        
    Example (market order):
        # Buy 5 YES contracts at market price
        order = place_kalshi_order(
            ticker="KXBTC-24DEC31-T100000",
            side="yes",
            action="buy",
            count=5
        )
        
    Example (limit order):
        # Buy 10 YES contracts at 45 cents
        order = place_kalshi_order(
            ticker="KXBTC-24DEC31-T100000",
            side="yes",
            action="buy",
            count=10,
            order_type="limit",
            price=45
        )
    """
    # Validate inputs
    if side not in ("yes", "no"):
        return {"error": "side must be 'yes' or 'no'"}
    if action not in ("buy", "sell"):
        return {"error": "action must be 'buy' or 'sell'"}
    if count < 1:
        return {"error": "count must be at least 1"}
    if order_type not in ("market", "limit"):
        return {"error": "order_type must be 'market' or 'limit'"}
    if order_type == "limit" and price is None:
        return {"error": "price is required for limit orders"}
    if price is not None and (price < 1 or price > 99):
        return {"error": "price must be between 1 and 99 cents"}
    
    async def execute(client):
        return await client.create_order(
            ticker=ticker,
            side=side,
            action=action,
            count=count,
            type=order_type,
            price=price
        )
    
    try:
        return _run_with_client(execute)
    except Exception as e:
        return {"error": f"Failed to place order: {str(e)}"}


def get_kalshi_orders(
    ticker: Optional[str] = None,
    status: str = "resting"
) -> Dict[str, Any]:
    """
    Get your Kalshi orders.
    
    Args:
        ticker: Optional market ticker to filter by
        status: Order status filter - "resting", "pending", "executed", "canceled"
                (default "resting" = open orders)
        
    Returns:
        dict with:
        - orders: List of order dicts
        - count: Number of orders
        
    Each order contains:
        - order_id: Unique order ID
        - ticker: Market ticker
        - status: Order status
        - side: "yes" or "no"
        - action: "buy" or "sell"
        - type: "market" or "limit"
        - yes_price/no_price: Limit price (if applicable)
        - remaining_count: Contracts remaining to fill
        - created_time: When the order was created
        
    Example:
        # Get all open orders
        orders = get_kalshi_orders()
        
        # Get executed orders for a specific market
        orders = get_kalshi_orders(ticker="KXBTC-24DEC31-T100000", status="executed")
    """
    async def fetch(client):
        result = await client.get_orders(ticker=ticker, status=status)
        orders = result.get("orders", [])
        return {
            "orders": orders,
            "count": len(orders)
        }
    
    try:
        return _run_with_client(fetch)
    except Exception as e:
        return {"error": f"Failed to get orders: {str(e)}"}


def cancel_kalshi_order(order_id: str) -> Dict[str, Any]:
    """
    Cancel a resting order on Kalshi.
    
    Args:
        order_id: The order ID to cancel
        
    Returns:
        dict with:
        - order_id: The canceled order ID
        - status: "canceled"
        
    Example:
        result = cancel_kalshi_order("abc123-order-id")
        if 'error' not in result:
            print(f"Order {result['order_id']} canceled")
    """
    async def execute(client):
        return await client.cancel_order(order_id)
    
    try:
        return _run_with_client(execute)
    except Exception as e:
        return {"error": f"Failed to cancel order: {str(e)}"}
