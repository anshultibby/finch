"""Get positions for a specific account"""
from typing import Dict, Any
from skills.snaptrade.scripts._client import get_snaptrade_client


def get_positions(user_id: str, account_id: str) -> Dict[str, Any]:
    """
    Get equity positions for a specific account.

    Args:
        user_id: User's ID
        account_id: SnapTrade account ID

    Returns:
        dict with:
            - success (bool)
            - positions (list): Position objects
            - count (int)

    Example:
        from skills.snaptrade.scripts.account.get_positions import get_positions
        result = get_positions('user-123', 'acct-456')
        for p in result['positions']:
            print(p)
    """
    client = get_snaptrade_client()

    try:
        session = client._get_session(user_id)
        if not session or not session.is_connected:
            return {"success": False, "needs_auth": True, "error": "Not connected"}

        response = client.client.account_information.get_user_account_positions(
            user_id=session.snaptrade_user_id,
            user_secret=session.snaptrade_user_secret,
            account_id=account_id,
        )
        data = response.body if hasattr(response, "body") else response
        positions = data if isinstance(data, list) else [data]
        return {"success": True, "positions": positions, "count": len(positions)}
    except Exception as e:
        return {"success": False, "error": str(e)}
