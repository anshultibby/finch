"""Delete a brokerage connection entirely"""
from typing import Dict, Any
from skills.snaptrade.scripts._client import get_snaptrade_client


def delete_connection(user_id: str, authorization_id: str) -> Dict[str, Any]:
    """
    Delete an entire brokerage connection (removes all accounts under it).

    Args:
        user_id: User's ID
        authorization_id: Brokerage authorization ID (from list_connections)

    Returns:
        dict with:
            - success (bool)
            - message (str)

    Example:
        from skills.snaptrade.scripts.connections.delete_connection import delete_connection
        result = delete_connection('user-123', 'auth-456')
        print(result['message'])
    """
    client = get_snaptrade_client()

    try:
        session = client._get_session(user_id)
        if not session:
            return {"success": False, "needs_auth": True, "error": "No session"}

        client.client.connections.remove_brokerage_authorization(
            authorization_id=authorization_id,
            user_id=session.snaptrade_user_id,
            user_secret=session.snaptrade_user_secret,
        )
        return {"success": True, "message": f"Connection {authorization_id} deleted"}
    except Exception as e:
        return {"success": False, "error": str(e)}
