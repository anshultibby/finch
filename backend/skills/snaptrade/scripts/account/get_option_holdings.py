"""Get option positions for a specific account"""
from typing import Dict, Any
from skills.snaptrade.scripts._client import get_snaptrade_client


def get_option_holdings(user_id: str, account_id: str) -> Dict[str, Any]:
    """
    List option positions for an account.

    Args:
        user_id: User's ID
        account_id: SnapTrade account ID

    Returns:
        dict with:
            - success (bool)
            - options (list): Option position objects
            - count (int)

    Example:
        from skills.snaptrade.scripts.account.get_option_holdings import get_option_holdings
        result = get_option_holdings('user-123', 'acct-456')
        for opt in result['options']:
            print(opt)
    """
    client = get_snaptrade_client()

    try:
        session = client._get_session(user_id)
        if not session or not session.is_connected:
            return {"success": False, "needs_auth": True, "error": "Not connected"}

        response = client.client.options.list_option_holdings(
            user_id=session.snaptrade_user_id,
            user_secret=session.snaptrade_user_secret,
            account_id=account_id,
        )
        data = response.body if hasattr(response, "body") else response
        options = data if isinstance(data, list) else [data]
        return {"success": True, "options": options, "count": len(options)}
    except Exception as e:
        return {"success": False, "error": str(e)}
