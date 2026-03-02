"""
Kalshi Trading — portfolio, markets, and order management.

All functions are synchronous. Do not await them.

Credentials from env vars:
  KALSHI_API_KEY_ID  — your Kalshi API key ID
  KALSHI_PRIVATE_KEY — RSA private key in PEM format

Prices are in CENTS (0–100). Quantities are integer contracts.
"""
from typing import Optional
from ._client import create_client, _NO_CREDS

_client = None


def _api():
    global _client
    if _client is None:
        _client = create_client()
    return _client


# ---------------------------------------------------------------------------
# Portfolio
# ---------------------------------------------------------------------------

def get_balance() -> dict:
    """
    Get Kalshi account balance.

    Returns: {balance: float (USD), portfolio_value: float (USD)}
    """
    c = _api()
    if not c:
        return _NO_CREDS
    r = c.get("/portfolio/balance")
    return {
        "balance":         r["balance"] / 100,
        "portfolio_value": r["portfolio_value"] / 100,
    }


def get_positions(limit: int = 100) -> dict:
    """
    Get current Kalshi positions.

    Returns: {positions: list, count: int}
    Each position: {ticker, position, market_exposure, realized_pnl, fees_paid}
    """
    c = _api()
    if not c:
        return _NO_CREDS
    r = c.get("/portfolio/positions", params={"limit": limit})
    positions = []
    for ep in (r.get("event_positions") or []):
        for mp in (ep.get("market_positions") or []):
            positions.append({
                "ticker":          mp.get("ticker"),
                "position":        mp.get("position"),
                "market_exposure": mp.get("market_exposure"),
                "realized_pnl":    mp.get("realized_pnl"),
                "fees_paid":       mp.get("fees_paid"),
            })
    return {"positions": positions, "count": len(positions)}


def get_portfolio() -> dict:
    """
    Get full portfolio: balance + positions in one call.

    Returns: {balance, portfolio_value, positions, count}
    """
    bal = get_balance()
    if "error" in bal:
        return bal
    pos = get_positions()
    if "error" in pos:
        return pos
    return {**bal, **pos}


# ---------------------------------------------------------------------------
# Markets
# ---------------------------------------------------------------------------

def get_events(limit: int = 20, status: str = "open", series_ticker: str = None) -> dict:
    """
    Get Kalshi events (groups of related markets).

    Args:
        limit:         Max events to return (default 20)
        status:        "open", "closed", or "settled"
        series_ticker: Optional series filter (e.g. "KXNBA")

    Returns: {events: list, count: int}
    Each event: {event_ticker, title, category, markets: [...]}
    Markets: {ticker, yes_bid, yes_ask, no_bid, no_ask, last_price, volume} — all in CENTS
    """
    c = _api()
    if not c:
        return _NO_CREDS
    params = {"limit": limit, "status": status}
    if series_ticker:
        params["series_ticker"] = series_ticker
    r = c.get("/events", params=params)
    events = [
        {
            "event_ticker":  ev.get("event_ticker"),
            "title":         ev.get("title"),
            "category":      ev.get("category"),
            "series_ticker": ev.get("series_ticker"),
            "markets": [
                {
                    "ticker":        m.get("ticker"),
                    "yes_bid":       m.get("yes_bid"),
                    "yes_ask":       m.get("yes_ask"),
                    "no_bid":        m.get("no_bid"),
                    "no_ask":        m.get("no_ask"),
                    "last_price":    m.get("last_price"),
                    "volume":        m.get("volume"),
                    "open_interest": m.get("open_interest"),
                    "status":        m.get("status"),
                }
                for m in (ev.get("markets") or [])
            ],
        }
        for ev in (r.get("events") or [])
    ]
    return {"events": events, "count": len(events)}


def get_market(ticker: str) -> dict:
    """
    Get a specific Kalshi market by ticker.

    Returns: {ticker, event_ticker, title, yes_bid, yes_ask, no_bid, no_ask,
              last_price, volume, volume_24h, open_interest, status}
    All prices in CENTS (divide by 100 for dollars).
    """
    c = _api()
    if not c:
        return _NO_CREDS
    r = c.get(f"/markets/{ticker}")
    m = r.get("market", {})
    return {
        "ticker":        m.get("ticker"),
        "event_ticker":  m.get("event_ticker"),
        "title":         m.get("title", ""),
        "yes_bid":       m.get("yes_bid"),
        "yes_ask":       m.get("yes_ask"),
        "no_bid":        m.get("no_bid"),
        "no_ask":        m.get("no_ask"),
        "last_price":    m.get("last_price"),
        "volume":        m.get("volume"),
        "volume_24h":    m.get("volume_24h"),
        "open_interest": m.get("open_interest"),
        "status":        m.get("status"),
    }


def get_orderbook(ticker: str, depth: int = 10) -> dict:
    """
    Get the orderbook for a market.

    Args:
        ticker: Market ticker
        depth:  Number of price levels per side (default 10)

    Returns: {yes: [[price, size], ...], no: [[price, size], ...]}
    Prices in CENTS.
    """
    c = _api()
    if not c:
        return _NO_CREDS
    r = c.get(f"/markets/{ticker}/orderbook", params={"depth": depth})
    ob = r.get("orderbook", {})
    return {
        "yes": ob.get("yes", []),
        "no":  ob.get("no", []),
    }


def get_markets(limit: int = 100, status: str = "open", event_ticker: str = None,
                series_ticker: str = None) -> dict:
    """
    Get Kalshi markets directly (flat list, no event grouping).

    Args:
        limit:         Max markets to return
        status:        "open", "closed", or "settled"
        event_ticker:  Filter by event
        series_ticker: Filter by series

    Returns: {markets: list, count: int}
    """
    c = _api()
    if not c:
        return _NO_CREDS
    params = {"limit": limit, "status": status}
    if event_ticker:
        params["event_ticker"] = event_ticker
    if series_ticker:
        params["series_ticker"] = series_ticker
    r = c.get("/markets", params=params)
    markets = [
        {
            "ticker":        m.get("ticker"),
            "event_ticker":  m.get("event_ticker"),
            "title":         m.get("title", ""),
            "yes_bid":       m.get("yes_bid"),
            "yes_ask":       m.get("yes_ask"),
            "no_bid":        m.get("no_bid"),
            "no_ask":        m.get("no_ask"),
            "last_price":    m.get("last_price"),
            "volume":        m.get("volume"),
            "open_interest": m.get("open_interest"),
            "status":        m.get("status"),
            "close_time":    m.get("close_time"),
        }
        for m in (r.get("markets") or [])
    ]
    return {"markets": markets, "count": len(markets)}


# ---------------------------------------------------------------------------
# Trading
# ---------------------------------------------------------------------------

def place_order(
    ticker: str,
    side: str,
    action: str,
    count: int,
    order_type: str = "market",
    price: Optional[int] = None,
) -> dict:
    """
    Place a Kalshi order.

    Args:
        ticker:     Market ticker (e.g. "KXBTC-26FEB28-W100")
        side:       "yes" or "no"
        action:     "buy" or "sell"
        count:      Number of contracts (>= 1)
        order_type: "market" or "limit"
        price:      Limit price in cents (1–99, required for limit orders)

    Returns: {order_id, ticker, status, side, action, count}
    """
    if side not in ("yes", "no"):
        return {"error": "side must be 'yes' or 'no'"}
    if action not in ("buy", "sell"):
        return {"error": "action must be 'buy' or 'sell'"}
    if count < 1:
        return {"error": "count must be at least 1"}
    if order_type == "limit" and price is None:
        return {"error": "price is required for limit orders"}
    if price is not None and not (1 <= price <= 99):
        return {"error": "price must be between 1 and 99 cents"}

    c = _api()
    if not c:
        return _NO_CREDS

    body = {"ticker": ticker, "side": side, "action": action, "count": count, "type": order_type}
    if order_type == "limit" and price is not None:
        body["yes_price" if side == "yes" else "no_price"] = price

    r = c.post("/portfolio/orders", body=body)
    o = r.get("order", {})
    return {
        "order_id": o.get("order_id"),
        "ticker":   o.get("ticker"),
        "status":   o.get("status"),
        "side":     o.get("side"),
        "action":   o.get("action"),
        "count":    o.get("count") or o.get("remaining_count"),
    }


def get_orders(ticker: str = None, status: str = "resting") -> dict:
    """
    Get your Kalshi orders.

    Args:
        ticker: Optional market ticker filter
        status: "resting" (open), "pending", "executed", or "canceled"

    Returns: {orders: list, count: int}
    """
    c = _api()
    if not c:
        return _NO_CREDS
    params = {"status": status}
    if ticker:
        params["ticker"] = ticker
    r = c.get("/portfolio/orders", params=params)
    orders = [
        {
            "order_id":        o.get("order_id"),
            "ticker":          o.get("ticker"),
            "side":            o.get("side"),
            "action":          o.get("action"),
            "type":            o.get("type"),
            "yes_price":       o.get("yes_price"),
            "no_price":        o.get("no_price"),
            "remaining_count": o.get("remaining_count"),
            "status":          o.get("status"),
            "created_time":    o.get("created_time"),
        }
        for o in (r.get("orders") or [])
    ]
    return {"orders": orders, "count": len(orders)}


def cancel_order(order_id: str) -> dict:
    """
    Cancel a resting Kalshi order.

    Returns: {order_id, status: "canceled"}
    """
    c = _api()
    if not c:
        return _NO_CREDS
    r = c.delete(f"/portfolio/orders/{order_id}")
    o = r.get("order", {})
    return {
        "order_id": o.get("order_id", order_id),
        "status":   "canceled",
    }
