"""Get real-time quotes for stock symbols"""
from typing import Dict, Any, List
from skills.snaptrade.scripts._client import get_snaptrade_client


def get_quotes(user_id: str, account_id: str, symbols: List[str]) -> Dict[str, Any]:
    """
    Get real-time quotes for given symbols.

    Args:
        user_id: User's ID
        account_id: SnapTrade account ID
        symbols: List of ticker symbols (e.g. ["AAPL", "TSLA"])

    Returns:
        dict with:
            - success (bool)
            - quotes (list): Quote objects with bid, ask, last price, volume

    Example:
        from skills.snaptrade.scripts.trading.get_quotes import get_quotes
        result = get_quotes('user-123', 'acct-456', ['AAPL', 'TSLA', 'MSFT'])
        for q in result['quotes']:
            print(q)
    """
    client = get_snaptrade_client()

    try:
        session = client._get_session(user_id)
        if not session or not session.is_connected:
            return {"success": False, "needs_auth": True, "error": "Not connected"}

        response = client.client.trading.get_user_account_quotes(
            user_id=session.snaptrade_user_id,
            user_secret=session.snaptrade_user_secret,
            account_id=account_id,
            symbols=",".join(symbols),
        )
        data = response.body if hasattr(response, "body") else response
        quotes = data if isinstance(data, list) else [data]
        return {"success": True, "quotes": quotes}
    except Exception as e:
        return {"success": False, "error": str(e)}
