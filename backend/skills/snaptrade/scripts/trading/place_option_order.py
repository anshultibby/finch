"""Place an option order"""
from typing import Dict, Any, List, Optional
from skills.snaptrade.scripts._client import get_snaptrade_client


def place_option_order(
    user_id: str,
    account_id: str,
    order_type: str,
    time_in_force: str,
    legs: List[Dict[str, Any]],
    price: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Place a multi-leg option order.

    Args:
        user_id: User's ID
        account_id: SnapTrade account ID
        order_type: "Market", "Limit", "NetDebit", "NetCredit"
        time_in_force: "Day", "GTC", "FOK"
        legs: List of leg dicts, each with:
            - symbol: Option symbol ID
            - action: "BUY_TO_OPEN", "BUY_TO_CLOSE", "SELL_TO_OPEN", "SELL_TO_CLOSE"
            - quantity: Number of contracts
        price: Net price for the spread (for Limit/NetDebit/NetCredit)

    Returns:
        dict with:
            - success (bool)
            - order (dict): Order result

    Example:
        from skills.snaptrade.scripts.trading.place_option_order import place_option_order
        legs = [
            {"symbol": "opt-id-1", "action": "BUY_TO_OPEN", "quantity": 1},
            {"symbol": "opt-id-2", "action": "SELL_TO_OPEN", "quantity": 1},
        ]
        result = place_option_order('user-123', 'acct-456', 'Limit', 'Day', legs, price=2.50)
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
            "order_type": order_type,
            "time_in_force": time_in_force,
            "legs": legs,
        }
        if price is not None:
            kwargs["price"] = price

        response = client.client.trading.place_mleg_order(**kwargs)
        data = response.body if hasattr(response, "body") else response
        return {"success": True, "order": data}
    except Exception as e:
        return {"success": False, "error": str(e)}
