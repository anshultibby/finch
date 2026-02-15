"""
Polymarket Trading - Trade Execution History via Dome API

Get actual BUY/SELL trade executions from Polymarket via Dome's /polymarket/orders endpoint.
This provides real execution data including prices, shares, and wallet addresses.
"""
from .._client import call_dome_api
from ..models import GetOrdersInput, GetOrdersOutput


def get_orders(input: GetOrdersInput) -> GetOrdersOutput:
    """
    Get executed orders (actual BUY/SELL trades) from Polymarket.
    
    This is the primary endpoint for fetching real trade execution data.
    Returns filled orders with price, shares, and transaction details.
    
    Args:
        input: GetOrdersInput with filters
        
    Returns:
        GetOrdersOutput with orders list and pagination
        
    Example:
        from servers.dome.models import GetOrdersInput
        orders = get_orders(GetOrdersInput(
            user="0x6a72f618...",
            limit=100
        ))
        for order in orders.orders:
            print(f"{order.side} {order.shares_normalized:.2f} @ ${order.price:.2f}")
    """
    params = input.model_dump(exclude_none=True)
    result = call_dome_api("/polymarket/orders", params)
    return GetOrdersOutput(**result)


def get_trade_history(input: GetOrdersInput) -> GetOrdersOutput:
    """
    Alias for get_orders() - Get executed trades from Polymarket.
    
    DEPRECATED: Use get_orders() instead for clarity.
    This function is kept for backward compatibility.
    """
    return get_orders(input)
