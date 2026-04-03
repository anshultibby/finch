"""Get orders for a specific brokerage account"""
from typing import Dict, Any, Optional
from skills.snaptrade.scripts._client import get_snaptrade_client


def get_orders(user_id: str, account_id: str, state: Optional[str] = None) -> Dict[str, Any]:
    """
    List orders for a specific account.

    Args:
        user_id: User's ID
        account_id: SnapTrade account ID
        state: Optional filter - "Executed", "Canceled", "Pending", etc.

    Returns:
        dict with:
            - success (bool)
            - orders (list): Order objects with id, symbol, action, status, quantity, price, etc.
            - count (int)

    Example:
        from skills.snaptrade.scripts.account.get_orders import get_orders
        result = get_orders('user-123', 'acct-456')
        for o in result['orders']:
            print(f"{o.get('action')} {o.get('symbol')} - {o.get('status')}")
    """
    client = get_snaptrade_client()

    try:
        session = client._get_session(user_id)
        if not session or not session.is_connected:
            return {"success": False, "needs_auth": True, "error": "Not connected"}

        kwargs = {
            "user_id": session.snaptrade_user_id,
            "user_secret": session.snaptrade_user_secret,
            "account_id": account_id,
        }
        if state:
            kwargs["state"] = state

        response = client.client.account_information.get_user_account_orders(**kwargs)
        data = response.body if hasattr(response, "body") else response
        orders = data if isinstance(data, list) else [data]
        return {"success": True, "orders": orders, "count": len(orders)}
    except Exception as e:
        return {"success": False, "error": str(e)}
