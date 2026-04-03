"""Cancel an open order"""
from typing import Dict, Any
from skills.snaptrade.scripts._client import get_snaptrade_client


def cancel_order(user_id: str, account_id: str, order_id: str) -> Dict[str, Any]:
    """
    Cancel an open/pending order on the brokerage.

    Args:
        user_id: User's ID
        account_id: SnapTrade account ID
        order_id: Brokerage order ID to cancel

    Returns:
        dict with:
            - success (bool)
            - result (dict): Cancellation result

    Example:
        from skills.snaptrade.scripts.trading.cancel_order import cancel_order
        result = cancel_order('user-123', 'acct-456', 'order-789')
        print(result)
    """
    client = get_snaptrade_client()

    try:
        session = client._get_session(user_id)
        if not session or not session.is_connected:
            return {"success": False, "needs_auth": True, "error": "Not connected"}

        response = client.client.trading.cancel_user_account_order(
            user_id=session.snaptrade_user_id,
            user_secret=session.snaptrade_user_secret,
            account_id=account_id,
            body={"brokerage_order_id": order_id},
        )
        data = response.body if hasattr(response, "body") else response
        return {"success": True, "result": data}
    except Exception as e:
        return {"success": False, "error": str(e)}
