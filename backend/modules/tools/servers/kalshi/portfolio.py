"""
Kalshi Portfolio APIs

Get balance, positions, and portfolio data from Kalshi.
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


def get_kalshi_balance() -> Dict[str, Any]:
    """
    Get your Kalshi account balance.
    
    Returns:
        dict with:
        - balance: Account balance in dollars
        - portfolio_value: Portfolio value in dollars
        
    Example:
        balance = get_kalshi_balance()
        if 'error' not in balance:
            print(f"Balance: ${balance['balance']:.2f}")
    """
    async def fetch(client):
        result = await client.get_balance()
        # Convert cents to dollars
        return {
            "balance": result.get("balance", 0) / 100,
            "portfolio_value": result.get("portfolio_value", 0) / 100,
        }
    
    try:
        return _run_with_client(fetch)
    except Exception as e:
        return {"error": f"Failed to get balance: {str(e)}"}


def get_kalshi_positions(limit: int = 100) -> Dict[str, Any]:
    """
    Get your current Kalshi positions.
    
    Args:
        limit: Maximum number of positions to return (default 100)
        
    Returns:
        dict with:
        - positions: List of position dicts with ticker, position, market_exposure, etc.
        - count: Number of positions
        
    Example:
        positions = get_kalshi_positions()
        if 'error' not in positions:
            for pos in positions['positions']:
                print(f"{pos['ticker']}: {pos['position']} contracts")
    """
    async def fetch(client):
        result = await client.get_positions(limit=limit)
        positions = result.get("positions", [])
        return {
            "positions": positions,
            "count": len(positions)
        }
    
    try:
        return _run_with_client(fetch)
    except Exception as e:
        return {"error": f"Failed to get positions: {str(e)}"}


def get_kalshi_portfolio() -> Dict[str, Any]:
    """
    Get full Kalshi portfolio (balance + positions).
    
    Returns:
        dict with:
        - balance: Account balance in dollars
        - portfolio_value: Portfolio value in dollars
        - positions: List of current positions
        - fetched_at: Timestamp of when data was fetched
        
    Example:
        portfolio = get_kalshi_portfolio()
        if 'error' not in portfolio:
            print(f"Balance: ${portfolio['balance']:.2f}")
            print(f"Positions: {len(portfolio['positions'])}")
    """
    async def fetch(client):
        result = await client.get_portfolio()
        # Convert balance from cents to dollars
        balance_data = result.get("balance", {})
        return {
            "balance": balance_data.get("balance", 0) / 100,
            "portfolio_value": balance_data.get("portfolio_value", 0) / 100,
            "positions": result.get("positions", []),
            "fetched_at": result.get("fetched_at")
        }
    
    try:
        return _run_with_client(fetch)
    except Exception as e:
        return {"error": f"Failed to get portfolio: {str(e)}"}
