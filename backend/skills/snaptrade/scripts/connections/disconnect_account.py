"""Disconnect a brokerage account"""
from typing import Dict, Any
from skills.snaptrade.scripts._client import get_snaptrade_client


def disconnect_account(user_id: str, account_id: str) -> Dict[str, Any]:
    """
    Disconnect a specific brokerage account.

    Args:
        user_id: User's ID
        account_id: SnapTrade account ID to disconnect

    Returns:
        dict with:
            - success (bool)
            - message (str)

    Example:
        from skills.snaptrade.scripts.connections.disconnect_account import disconnect_account
        result = disconnect_account('user-123', 'acct-456')
        print(result['message'])
    """
    client = get_snaptrade_client()

    try:
        session = client._get_session(user_id)
        if not session or not session.is_connected:
            return {"success": False, "needs_auth": True, "error": "Not connected"}

        client.client.account_information.delete_user_account(
            user_id=session.snaptrade_user_id,
            user_secret=session.snaptrade_user_secret,
            account_id=account_id,
        )
        return {"success": True, "message": f"Account {account_id} disconnected"}
    except Exception as e:
        return {"success": False, "error": str(e)}
