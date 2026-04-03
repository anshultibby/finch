"""Force refresh data from a brokerage connection"""
from typing import Dict, Any
from skills.snaptrade.scripts._client import get_snaptrade_client


def refresh_connection(user_id: str, authorization_id: str) -> Dict[str, Any]:
    """
    Force refresh holdings data from a brokerage connection.
    Use when data seems stale or after recent trades.

    Args:
        user_id: User's ID
        authorization_id: Brokerage authorization ID (from list_connections)

    Returns:
        dict with:
            - success (bool)
            - result (dict): Refresh result

    Example:
        from skills.snaptrade.scripts.connections.refresh_connection import refresh_connection
        result = refresh_connection('user-123', 'auth-456')
        print(result)
    """
    client = get_snaptrade_client()

    try:
        session = client._get_session(user_id)
        if not session or not session.is_connected:
            return {"success": False, "needs_auth": True, "error": "Not connected"}

        response = client.client.connections.refresh_brokerage_authorization(
            authorization_id=authorization_id,
            user_id=session.snaptrade_user_id,
            user_secret=session.snaptrade_user_secret,
        )
        data = response.body if hasattr(response, "body") else response
        return {"success": True, "result": data}
    except Exception as e:
        return {"success": False, "error": str(e)}
