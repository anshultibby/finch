"""
Server-side SnapTrade helper functions used by routes.
Thin wrappers around snaptrade_tools that handle session lookup.

NOTE: These functions are synchronous (called via asyncio.to_thread from routes).
They rely on _get_session_sync which checks the in-memory cache first, then
falls back to a synchronous DB query.
"""
from typing import Dict, Any, Optional
from modules.tools.clients.snaptrade import snaptrade_tools


def _get_session_sync(user_id: str):
    """Get SnapTrade session synchronously (cache-first, sync DB fallback)."""
    if user_id in snaptrade_tools._sessions:
        return snaptrade_tools._sessions[user_id]

    from core.database import SessionLocal
    from crud.snaptrade_user import get_user_by_id
    from modules.tools.clients.snaptrade import SnapTradeSession

    db = SessionLocal()
    try:
        db_user = get_user_by_id(db, user_id)
        if db_user and db_user.snaptrade_user_secret:
            session = SnapTradeSession(
                snaptrade_user_id=db_user.snaptrade_user_id,
                snaptrade_user_secret=db_user.snaptrade_user_secret,
                is_connected=db_user.is_connected,
                last_activity=db_user.last_activity.isoformat(),
                account_ids=db_user.connected_account_ids.split(',') if db_user.connected_account_ids else []
            )
            snaptrade_tools._sessions[user_id] = session
            return session
    finally:
        db.close()
    return None


def search_symbols(user_id: str, account_id: str, query: str) -> Dict[str, Any]:
    """Search for tradeable symbols within a brokerage account."""
    try:
        session = _get_session_sync(user_id)
        if not session or not session.is_connected:
            return {"success": False, "needs_auth": True, "error": "Not connected"}

        response = snaptrade_tools.client.reference_data.symbol_search_user_account(
            user_id=session.snaptrade_user_id,
            user_secret=session.snaptrade_user_secret,
            account_id=account_id,
            body={"substring": query},
        )
        data = response.body if hasattr(response, "body") else response
        symbols = data if isinstance(data, list) else [data]
        return {"success": True, "symbols": symbols, "count": len(symbols)}
    except Exception as e:
        return {"success": False, "error": str(e)}


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
    """Place an equity order directly (force, no preview step)."""
    try:
        session = _get_session_sync(user_id)
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

        response = snaptrade_tools.client.trading.place_force_order(**kwargs)
        data = response.body if hasattr(response, "body") else response
        return {"success": True, "order": data}
    except Exception as e:
        return {"success": False, "error": str(e)}
