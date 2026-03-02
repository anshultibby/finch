"""
Kalshi API client — uses the official kalshi_python_async SDK.
Used server-side (e.g. strategy execution context).
"""
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from kalshi_python_async import (
    KalshiClient as KalshiSDKClient,
    KalshiAuth,
    Configuration,
    PortfolioApi,
    EventsApi,
    MarketApi,
    OrdersApi,
)

logger = logging.getLogger(__name__)

KALSHI_API_HOST = "https://api.elections.kalshi.com/trade-api/v2"


class KalshiClient:
    """
    Kalshi API client wrapper.

    Usage:
        client = KalshiClient(api_key_id, private_key_pem)
        balance = await client.get_balance()
    """

    def __init__(self, api_key_id: str, private_key_pem: str):
        config = Configuration()
        config.host = KALSHI_API_HOST
        self._sdk = KalshiSDKClient(configuration=config)
        self._sdk.kalshi_auth = KalshiAuth(api_key_id, private_key_pem)
        self._portfolio = PortfolioApi(self._sdk)
        self._events    = EventsApi(self._sdk)
        self._market    = MarketApi(self._sdk)
        self._orders    = OrdersApi(self._sdk)

    async def close(self):
        try:
            await self._sdk.rest_client.close()
        except Exception:
            pass

    async def get_balance(self) -> Dict[str, Any]:
        r = await self._portfolio.get_balance()
        return {"balance": r.balance, "portfolio_value": r.portfolio_value}

    async def get_positions(self, limit: int = 100) -> Dict[str, Any]:
        r = await self._portfolio.get_positions(limit=limit)
        positions = []
        for ep in (r.event_positions or []):
            for mp in (ep.market_positions or []):
                positions.append({
                    "ticker":               mp.ticker,
                    "position":             mp.position,
                    "market_exposure":      mp.market_exposure,
                    "realized_pnl":         mp.realized_pnl,
                    "total_traded":         mp.total_traded,
                    "resting_orders_count": mp.resting_orders_count,
                    "fees_paid":            mp.fees_paid,
                })
        return {"positions": positions, "cursor": r.cursor}

    async def get_portfolio(self) -> Dict[str, Any]:
        balance   = await self.get_balance()
        positions = await self.get_positions()
        return {
            "balance":    balance,
            "positions":  positions.get("positions", []),
            "fetched_at": datetime.utcnow().isoformat(),
        }

    async def get_events(self, limit: int = 20, status: str = "open") -> Dict[str, Any]:
        r = await self._events.get_events(limit=limit, status=status)
        events = [
            {
                "event_ticker":       ev.event_ticker,
                "title":              ev.title,
                "category":           ev.category,
                "series_ticker":      ev.series_ticker,
                "mutually_exclusive": ev.mutually_exclusive,
            }
            for ev in (r.events or [])
        ]
        return {"events": events, "cursor": r.cursor}

    async def get_event(self, event_ticker: str) -> Dict[str, Any]:
        r  = await self._events.get_event(event_ticker=event_ticker)
        ev = r.event
        return {
            "event_ticker":       ev.event_ticker,
            "title":              ev.title,
            "category":           ev.category,
            "series_ticker":      ev.series_ticker,
            "mutually_exclusive": ev.mutually_exclusive,
            "markets":            [m.ticker for m in (ev.markets or [])],
        }

    async def get_market(self, ticker: str) -> Dict[str, Any]:
        r = await self._market.get_market(ticker=ticker)
        m = r.market
        return {
            "ticker":        m.ticker,
            "event_ticker":  m.event_ticker,
            "status":        m.status,
            "yes_bid":       m.yes_bid,
            "yes_ask":       m.yes_ask,
            "no_bid":        m.no_bid,
            "no_ask":        m.no_ask,
            "last_price":    m.last_price,
            "volume":        m.volume,
            "volume_24h":    m.volume_24h,
            "open_interest": m.open_interest,
        }

    async def create_order(
        self,
        ticker: str,
        side: str,
        action: str,
        count: int,
        type: str = "market",
        price: Optional[int] = None,
    ) -> Dict[str, Any]:
        from kalshi_python_async import CreateOrderRequest
        req = CreateOrderRequest(ticker=ticker, side=side, action=action, count=count, type=type)
        if type == "limit" and price is not None:
            if side == "yes":
                req.yes_price = price
            else:
                req.no_price = price
        r = await self._orders.create_order(create_order_request=req)
        o = r.order
        return {
            "order_id": o.order_id,
            "ticker":   o.ticker,
            "status":   o.status,
            "side":     o.side,
            "action":   o.action,
            "count":    getattr(o, "count", None) or o.remaining_count,
        }

    async def get_orders(self, ticker: Optional[str] = None, status: str = "resting") -> Dict[str, Any]:
        kwargs = {"status": status}
        if ticker:
            kwargs["ticker"] = ticker
        r = await self._orders.get_orders(**kwargs)
        orders = [
            {
                "order_id":        o.order_id,
                "ticker":          o.ticker,
                "status":          o.status,
                "side":            o.side,
                "action":          o.action,
                "type":            o.type,
                "yes_price":       o.yes_price,
                "no_price":        o.no_price,
                "remaining_count": o.remaining_count,
                "created_time":    o.created_time,
            }
            for o in (r.orders or [])
        ]
        return {"orders": orders, "cursor": r.cursor}

    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        r = await self._orders.cancel_order(order_id=order_id)
        return {"order_id": r.order.order_id if r.order else order_id, "status": "canceled"}


async def test_kalshi_credentials(api_key_id: str, private_key_pem: str) -> Dict[str, Any]:
    """Test Kalshi credentials by fetching balance."""
    try:
        client = KalshiClient(api_key_id, private_key_pem)
    except Exception as e:
        return {"success": False, "message": f"Failed to load private key: {e}"}

    try:
        balance = await client.get_balance()
        await client.close()
        dollars = balance.get("balance", 0) / 100
        return {"success": True, "message": f"Credentials valid! Balance: ${dollars:.2f}", "balance": dollars}
    except Exception as e:
        await client.close()
        msg = str(e)
        logger.warning(f"Kalshi credential test failed: {msg}")
        if "401" in msg or "Unauthorized" in msg:
            return {"success": False, "message": "Invalid credentials. Check that your API Key ID matches the private key."}
        if "signature" in msg.lower():
            return {"success": False, "message": "Signature error. Make sure you're using the correct private key."}
        return {"success": False, "message": f"Connection error: {msg}"}
