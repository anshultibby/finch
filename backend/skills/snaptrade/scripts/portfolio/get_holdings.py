"""Get user's current portfolio holdings"""
from typing import Dict, Any
from servers.snaptrade._client import get_snaptrade_client


async def get_holdings(user_id: str) -> Dict[str, Any]:
    """
    Fetch user's current brokerage portfolio holdings
    
    Args:
        user_id: User's ID in your system
        
    Returns:
        dict with:
            - success (bool): Whether fetch succeeded
            - data (dict): Portfolio data with holdings in CSV format
            - needs_auth (bool): True if user needs to connect brokerage
            - error (str): Error message if any
            
    Example:
        holdings = await get_holdings('user-123')
        if holdings['success']:
            print(holdings['data']['csv'])
        elif holdings.get('needs_auth'):
            # User needs to connect brokerage
            pass
    
    Security:
        - OAuth authentication via SnapTrade
        - No credentials stored or passed through your app
        - Connection persists across sessions
    """
    client = get_snaptrade_client()
    
    # Use existing async method that handles everything
    result = None
    async for item in client.get_portfolio_streaming(user_id):
        if not isinstance(item, dict):
            continue
        result = item
    
    return result or {"success": False, "error": "No data returned"}

