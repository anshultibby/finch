"""Place an equity order through connected brokerage"""
from typing import Dict, Any, Optional
from skills.snaptrade.scripts._client import get_snaptrade_client


def place_order(
    user_id: str,
    account_id: str,
    action: str,
    symbol: str,
    order_type: str,
    time_in_force: str,
    quantity: Optional[float] = None,
    price: Optional[float] = None,
    stop: Optional[float] = None,
    notional_value: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Place an equity order directly (force, no preview step).

    Args:
        user_id: User's ID
        account_id: SnapTrade account ID
        action: "BUY" or "SELL"
        symbol: Universal symbol ID (use search_symbols to find)
        order_type: "Market", "Limit", "StopLimit", or "StopLoss"
        time_in_force: "Day", "GTC" (good til cancelled), "FOK" (fill or kill)
        quantity: Number of shares (optional if using notional_value)
        price: Limit price (required for Limit/StopLimit)
        stop: Stop price (required for StopLimit/StopLoss)
        notional_value: Dollar amount (alternative to quantity, for fractional shares)

    Returns:
        dict with:
            - success (bool)
            - order (dict): Order result from brokerage

    Example:
        from skills.snaptrade.scripts.trading.place_order import place_order
        result = place_order('user-123', 'acct-456', 'BUY', 'symbol-id', 'Limit', 'Day', quantity=10, price=150.00)
        print(result)
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
        if stop is not None:
            kwargs["stop"] = stop
        if notional_value is not None:
            kwargs["notional_value"] = notional_value

        response = client.client.trading.place_force_order(**kwargs)
        data = response.body if hasattr(response, "body") else response
        return {"success": True, "order": data}
    except Exception as e:
        return {"success": False, "error": str(e)}
