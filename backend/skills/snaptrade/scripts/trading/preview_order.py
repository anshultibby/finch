"""Preview order impact before placing"""
from typing import Dict, Any, Optional
from skills.snaptrade.scripts._client import get_snaptrade_client


def preview_order(
    user_id: str,
    account_id: str,
    action: str,
    symbol: str,
    order_type: str,
    time_in_force: str,
    quantity: Optional[float] = None,
    price: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Preview the impact of a trade before placing it.
    Shows estimated cost, commission, buying power effect, and warnings.

    Args:
        user_id: User's ID
        account_id: SnapTrade account ID
        action: "BUY" or "SELL"
        symbol: Universal symbol ID
        order_type: "Market", "Limit", "StopLimit", or "StopLoss"
        time_in_force: "Day", "GTC", "FOK"
        quantity: Number of shares
        price: Limit price (if applicable)

    Returns:
        dict with:
            - success (bool)
            - impact (dict): Trade impact details (cost, commission, buying power effect)
            - trade_id (str): Use with confirm_order to place it

    Example:
        from skills.snaptrade.scripts.trading.preview_order import preview_order
        result = preview_order('user-123', 'acct-456', 'BUY', 'symbol-id', 'Limit', 'Day', quantity=10, price=150.00)
        if result['success']:
            print(f"Estimated cost: {result['impact']}")
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
            "action": action,
            "universal_symbol_id": symbol,
            "order_type": order_type,
            "time_in_force": time_in_force,
        }
        if quantity is not None:
            kwargs["units"] = quantity
        if price is not None:
            kwargs["price"] = price

        response = client.client.trading.get_order_impact(**kwargs)
        data = response.body if hasattr(response, "body") else response
        return {"success": True, "impact": data}
    except Exception as e:
        return {"success": False, "error": str(e)}
