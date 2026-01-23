"""
Kalshi API Client using official SDK

SECURITY:
- Private keys are passed in-memory, never stored in this module
- Credentials come from encrypted storage via CRUD layer
- All credential handling is done server-side only
"""
from typing import Optional, Dict, Any
from datetime import datetime
import logging

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
    Kalshi API client wrapper around official SDK
    
    Usage:
        client = KalshiClient(api_key_id, private_key_pem)
        balance = await client.get_balance()
    """
    
    def __init__(self, api_key_id: str, private_key_pem: str):
        """
        Initialize Kalshi client
        
        Args:
            api_key_id: Kalshi API Key ID
            private_key_pem: RSA private key in PEM format
        """
        self.api_key_id = api_key_id
        
        # Set up configuration
        config = Configuration()
        config.host = KALSHI_API_HOST
        
        # Create auth and client
        auth = KalshiAuth(api_key_id, private_key_pem)
        self._client = KalshiSDKClient(configuration=config)
        self._client.kalshi_auth = auth
        
        # Initialize API instances
        self._portfolio = PortfolioApi(self._client)
        self._events = EventsApi(self._client)
        self._market = MarketApi(self._client)
        self._orders = OrdersApi(self._client)
    
    async def close(self):
        """Close the client connection"""
        try:
            await self._client.rest_client.close()
        except Exception:
            pass  # Ignore cleanup errors
    
    # ─────────────────────────────────────────────────────────────────────────
    # Portfolio Endpoints
    # ─────────────────────────────────────────────────────────────────────────
    
    async def get_balance(self) -> Dict[str, Any]:
        """
        Get account balance
        
        Returns:
            {"balance": cents, "portfolio_value": cents, ...}
        """
        response = await self._portfolio.get_balance()
        return {
            "balance": response.balance,
            "portfolio_value": response.portfolio_value,
            "updated_ts": response.updated_ts,
        }
    
    async def get_positions(self, limit: int = 100) -> Dict[str, Any]:
        """
        Get current positions
        
        Args:
            limit: Max positions to return
            
        Returns:
            {"positions": [...], "cursor": ...}
        """
        response = await self._portfolio.get_positions(limit=limit)
        positions = []
        if response.event_positions:
            for ep in response.event_positions:
                if ep.market_positions:
                    for mp in ep.market_positions:
                        positions.append({
                            "ticker": mp.ticker,
                            "position": mp.position,
                            "market_exposure": mp.market_exposure,
                            "realized_pnl": mp.realized_pnl,
                            "total_traded": mp.total_traded,
                            "resting_orders_count": mp.resting_orders_count,
                            "fees_paid": mp.fees_paid,
                        })
        return {
            "positions": positions,
            "cursor": response.cursor,
        }
    
    async def get_portfolio(self) -> Dict[str, Any]:
        """
        Get full portfolio summary (balance + positions)
        
        Returns:
            Combined balance and positions data
        """
        balance = await self.get_balance()
        positions = await self.get_positions()
        
        return {
            "balance": balance,
            "positions": positions.get("positions", []),
            "fetched_at": datetime.utcnow().isoformat()
        }
    
    # ─────────────────────────────────────────────────────────────────────────
    # Market Endpoints
    # ─────────────────────────────────────────────────────────────────────────
    
    async def get_events(self, limit: int = 20, status: str = "open") -> Dict[str, Any]:
        """
        Get events (prediction markets)
        
        Args:
            limit: Max events to return
            status: Filter by status (open, closed, settled)
        """
        response = await self._events.get_events(limit=limit, status=status)
        events = []
        if response.events:
            for event in response.events:
                events.append({
                    "event_ticker": event.event_ticker,
                    "title": event.title,
                    "subtitle": event.sub_title,
                    "category": event.category,
                    "series_ticker": event.series_ticker,
                    "mutually_exclusive": event.mutually_exclusive,
                })
        return {
            "events": events,
            "cursor": response.cursor,
        }
    
    async def get_event(self, event_ticker: str) -> Dict[str, Any]:
        """Get single event by ticker"""
        response = await self._events.get_event(event_ticker=event_ticker)
        event = response.event
        return {
            "event_ticker": event.event_ticker,
            "title": event.title,
            "subtitle": event.sub_title,
            "category": event.category,
            "series_ticker": event.series_ticker,
            "mutually_exclusive": event.mutually_exclusive,
            "markets": [m.ticker for m in event.markets] if event.markets else [],
        }
    
    async def get_market(self, ticker: str) -> Dict[str, Any]:
        """Get single market by ticker"""
        response = await self._market.get_market(ticker=ticker)
        market = response.market
        return {
            "ticker": market.ticker,
            "event_ticker": market.event_ticker,
            "status": market.status,
            "yes_bid": market.yes_bid,
            "yes_ask": market.yes_ask,
            "no_bid": market.no_bid,
            "no_ask": market.no_ask,
            "last_price": market.last_price,
            "volume": market.volume,
            "volume_24h": market.volume_24h,
            "open_interest": market.open_interest,
        }
    
    # ─────────────────────────────────────────────────────────────────────────
    # Trading Endpoints
    # ─────────────────────────────────────────────────────────────────────────
    
    async def create_order(
        self,
        ticker: str,
        side: str,  # "yes" or "no"
        action: str,  # "buy" or "sell"
        count: int,  # Number of contracts
        type: str = "market",  # "market" or "limit"
        price: Optional[int] = None  # Price in cents (for limit orders)
    ) -> Dict[str, Any]:
        """
        Create an order
        
        Args:
            ticker: Market ticker
            side: "yes" or "no"
            action: "buy" or "sell"
            count: Number of contracts
            type: Order type ("market" or "limit")
            price: Limit price in cents (required for limit orders)
            
        Returns:
            Order response with order_id
        """
        from kalshi_python_async import CreateOrderRequest
        
        request = CreateOrderRequest(
            ticker=ticker,
            side=side,
            action=action,
            count=count,
            type=type,
        )
        
        if type == "limit" and price is not None:
            if side == "yes":
                request.yes_price = price
            else:
                request.no_price = price
        
        response = await self._orders.create_order(create_order_request=request)
        order = response.order
        return {
            "order_id": order.order_id,
            "ticker": order.ticker,
            "status": order.status,
            "side": order.side,
            "action": order.action,
            "count": order.count if hasattr(order, 'count') else order.remaining_count,
        }
    
    async def get_orders(self, ticker: Optional[str] = None, status: str = "resting") -> Dict[str, Any]:
        """
        Get orders
        
        Args:
            ticker: Optional market ticker filter
            status: Order status (resting, pending, executed, canceled)
        """
        kwargs = {"status": status}
        if ticker:
            kwargs["ticker"] = ticker
            
        response = await self._orders.get_orders(**kwargs)
        orders = []
        if response.orders:
            for order in response.orders:
                orders.append({
                    "order_id": order.order_id,
                    "ticker": order.ticker,
                    "status": order.status,
                    "side": order.side,
                    "action": order.action,
                    "type": order.type,
                    "yes_price": order.yes_price,
                    "no_price": order.no_price,
                    "remaining_count": order.remaining_count,
                    "created_time": order.created_time,
                })
        return {
            "orders": orders,
            "cursor": response.cursor,
        }
    
    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel an order by ID"""
        response = await self._orders.cancel_order(order_id=order_id)
        return {
            "order_id": response.order.order_id if response.order else order_id,
            "status": "canceled",
        }


async def test_kalshi_credentials(api_key_id: str, private_key_pem: str) -> Dict[str, Any]:
    """
    Test Kalshi credentials by fetching balance
    
    Args:
        api_key_id: Kalshi API Key ID
        private_key_pem: RSA private key in PEM format
        
    Returns:
        {"success": bool, "message": str, "balance": float (if success)}
    """
    try:
        client = KalshiClient(api_key_id, private_key_pem)
    except ValueError as e:
        logger.warning(f"Kalshi credential test failed - key loading error: {e}")
        return {
            "success": False,
            "message": f"Invalid private key format: {e}. Make sure you copied the entire key including BEGIN/END lines."
        }
    except Exception as e:
        logger.warning(f"Kalshi credential test failed - unexpected error loading key: {e}")
        return {
            "success": False,
            "message": f"Failed to load private key: {e}"
        }
    
    try:
        balance_response = await client.get_balance()
        await client.close()
        
        # Balance is in cents
        balance_cents = balance_response.get("balance", 0)
        balance_dollars = balance_cents / 100
        
        return {
            "success": True,
            "message": f"Credentials valid! Balance: ${balance_dollars:.2f}",
            "balance": balance_dollars
        }
    except Exception as e:
        await client.close()
        error_msg = str(e)
        logger.warning(f"Kalshi credential test failed: {error_msg}")
        
        if "401" in error_msg or "Unauthorized" in error_msg:
            return {
                "success": False,
                "message": "Invalid credentials. Make sure the API Key ID matches the private key, and that the key hasn't been revoked."
            }
        elif "signature" in error_msg.lower():
            return {
                "success": False,
                "message": "Signature error. Make sure you're using the correct private key."
            }
        else:
            return {
                "success": False,
                "message": f"Connection error: {error_msg}"
            }
