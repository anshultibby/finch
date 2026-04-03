"""Search for tradeable symbols"""
from typing import Dict, Any
from skills.snaptrade.scripts._client import get_snaptrade_client


def search_symbols(user_id: str, account_id: str, query: str) -> Dict[str, Any]:
    """
    Search for tradeable symbols within a brokerage account.
    Returns matching stocks, ETFs, and other instruments with their universal symbol IDs.

    Args:
        user_id: User's ID
        account_id: SnapTrade account ID
        query: Search query (e.g. "AAPL", "Apple", "technology")

    Returns:
        dict with:
            - success (bool)
            - symbols (list): Symbol objects with id, ticker, name, exchange
            - count (int)

    Example:
        from skills.snaptrade.scripts.reference.search_symbols import search_symbols
        result = search_symbols('user-123', 'acct-456', 'AAPL')
        for s in result['symbols']:
            print(f"{s.get('symbol', {}).get('symbol')}: {s.get('symbol', {}).get('description')}")
    """
    client = get_snaptrade_client()

    try:
        session = client._get_session(user_id)
        if not session or not session.is_connected:
            return {"success": False, "needs_auth": True, "error": "Not connected"}

        response = client.client.reference_data.symbol_search_user_account(
            user_id=session.snaptrade_user_id,
            user_secret=session.snaptrade_user_secret,
            account_id=account_id,
            body={"substring": query},
        )
        data = response.body if hasattr(response, "body") else response
        symbols = data if isinstance(data, list) else [data]
        return {"success": True, "symbols": symbols, "count": len(symbols)}
    except Exception as e:
        return {"success": False, "error": str(e)}
