"""List all brokerage connections"""
from typing import Dict, Any
from skills.snaptrade.scripts._client import get_snaptrade_client


def list_connections(user_id: str) -> Dict[str, Any]:
    """
    List all brokerage connections/authorizations.

    Args:
        user_id: User's ID

    Returns:
        dict with:
            - success (bool)
            - connections (list): Connection objects with id, brokerage, status
            - count (int)

    Example:
        from skills.snaptrade.scripts.connections.list_connections import list_connections
        result = list_connections('user-123')
        for c in result['connections']:
            print(c)
    """
    client = get_snaptrade_client()

    try:
        session = client._get_session(user_id)
        if not session:
            return {"success": True, "connections": [], "count": 0, "message": "No session"}

        response = client.client.connections.list_brokerage_authorizations(
            user_id=session.snaptrade_user_id,
            user_secret=session.snaptrade_user_secret,
        )
        data = response.body if hasattr(response, "body") else response
        connections = data if isinstance(data, list) else [data]
        return {"success": True, "connections": connections, "count": len(connections)}
    except Exception as e:
        return {"success": False, "error": str(e)}
