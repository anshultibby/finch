"""Unified "recent executed trades" for the trade-feedback wedge (pillar 2).

Returns the user's last executed BUY/SELL trades from whichever brokerage they've
connected — Robinhood (agentic MCP, filled orders) or SnapTrade (the synced
`Transaction` table) — in one shape the trade-feedback UI ranks by recency, with
a `$ amount` for size emphasis. Realized P&L is intentionally not computed here
(deferred); the drill-down agent run assesses trade quality.
"""
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import desc, select

from core.database import get_db_session
from models.brokerage import Transaction

logger = logging.getLogger(__name__)


def _f(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def map_robinhood_order(o: dict) -> Optional[dict]:
    """One Robinhood filled equity order -> unified trade item (None if unusable)."""
    symbol = (o.get("symbol") or "").upper()
    side = (o.get("side") or "").upper()
    if not symbol or side not in ("BUY", "SELL"):
        return None
    qty = _f(o.get("quantity"))
    price = _f(o.get("average_price") if o.get("average_price") is not None else o.get("price"))
    return {
        "id": str(o.get("id") or f"{symbol}-{o.get('last_transaction_at') or o.get('created_at')}"),
        "symbol": symbol,
        "side": side,
        "quantity": qty,
        "price": round(price, 2),
        "amount": round(qty * price, 2),
        "date": o.get("last_transaction_at") or o.get("created_at"),
        "broker": "robinhood",
    }


def map_snaptrade_transaction(tx: Transaction) -> Optional[dict]:
    """One SnapTrade Transaction row -> unified trade item (None if unusable)."""
    symbol = (tx.symbol or "").upper()
    side = (tx.transaction_type or "").upper()
    if not symbol or side not in ("BUY", "SELL"):
        return None
    data = tx.data or {}
    qty = _f(data.get("quantity"))
    price = _f(data.get("price"))
    return {
        "id": str(tx.id),
        "symbol": symbol,
        "side": side,
        "quantity": qty,
        "price": round(price, 2),
        "amount": round(qty * price, 2),
        "date": tx.transaction_date.isoformat() if tx.transaction_date else None,
        "broker": "snaptrade",
    }


async def _robinhood_recent(user_id: str, limit: int) -> List[dict]:
    from services import robinhood_auth

    accounts_raw = await robinhood_auth.mcp_call(user_id, "get_accounts")
    accounts = (accounts_raw or {}).get("data", {}).get("accounts", []) if isinstance(accounts_raw, dict) else []
    agentic = next((a for a in accounts if a.get("agentic_allowed")), None)
    if not agentic:
        return []
    acct = agentic["account_number"]

    orders_raw = await robinhood_auth.mcp_call(
        user_id, "get_equity_orders", {"account_number": acct, "state": "filled"}
    )
    orders = (orders_raw or {}).get("data", {}).get("orders", []) if isinstance(orders_raw, dict) else []
    items = [m for m in (map_robinhood_order(o) for o in orders) if m]
    items.sort(key=lambda t: t.get("date") or "", reverse=True)
    return items[:limit]


async def _snaptrade_query(user_id: str, limit: int) -> List[Transaction]:
    async with get_db_session() as db:
        rows = (await db.execute(
            select(Transaction)
            .where(
                Transaction.user_id == user_id,
                Transaction.transaction_type.in_(("BUY", "SELL")),
            )
            .order_by(desc(Transaction.transaction_date))
            .limit(limit)
        )).scalars().all()
    return list(rows)


async def _snaptrade_recent(user_id: str, limit: int) -> List[dict]:
    rows = await _snaptrade_query(user_id, limit)
    if not rows:
        # No synced trades yet — try one sync, then re-query.
        try:
            from services.transaction_sync import transaction_sync_service
            await transaction_sync_service.sync_user_transactions(user_id=user_id)
        except Exception:
            logger.exception("recent_trades: snaptrade sync failed for %s", user_id)
        rows = await _snaptrade_query(user_id, limit)
    return [m for m in (map_snaptrade_transaction(tx) for tx in rows) if m]


async def get_recent_trades(user_id: str, limit: int = 15) -> Dict[str, Any]:
    """Last `limit` executed trades, newest-first, from the user's connected broker.

    Robinhood (the agentic trading path) takes precedence over SnapTrade. Returns
    {connected, broker, trades}; connected=False drives the UI's connect CTA.
    """
    from modules.tools.clients import snaptrade_tools
    from services import robinhood_auth

    try:
        if await robinhood_auth.is_connected(user_id):
            return {"connected": True, "broker": "robinhood",
                    "trades": await _robinhood_recent(user_id, limit)}
    except Exception:
        logger.exception("recent_trades: robinhood fetch failed for %s", user_id)

    try:
        if await snaptrade_tools.has_active_connection(user_id):
            return {"connected": True, "broker": "snaptrade",
                    "trades": await _snaptrade_recent(user_id, limit)}
    except Exception:
        logger.exception("recent_trades: snaptrade fetch failed for %s", user_id)

    return {"connected": False, "broker": None, "trades": []}
