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


def get_positions(limit: int = 100, count_filter: str = "position") -> dict:
    """
    Get current Kalshi positions.

    Args:
        limit:        Max positions to return (default 100)
        count_filter: Filter for non-zero fields. "position" (default) returns only
                      positions with non-zero contracts. "total_traded" includes any
                      market you've ever traded. None returns all.

    Returns: {positions: list, count: int}
    Each position: {ticker, position, market_exposure, market_exposure_dollars,
                    total_traded, realized_pnl, fees_paid, last_updated_ts}
    position > 0 means YES contracts, < 0 means NO contracts.
    """
    c = _api()
    if not c:
        return _NO_CREDS
    params = {"limit": limit}
    if count_filter:
        params["count_filter"] = count_filter
    r = c.get("/portfolio/positions", params=params)
    positions = [
        {
            "ticker":                  mp.get("ticker"),
            "position":                mp.get("position"),
            "market_exposure":         mp.get("market_exposure"),
            "market_exposure_dollars": mp.get("market_exposure_dollars"),
            "total_traded":            mp.get("total_traded"),
            "realized_pnl":            mp.get("realized_pnl"),
            "fees_paid":               mp.get("fees_paid"),
            "last_updated_ts":         mp.get("last_updated_ts"),
        }
        for mp in (r.get("market_positions") or [])
    ]
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


def get_fills(ticker: str = None, limit: int = 100, cursor: str = None) -> dict:
    """
    Get your recent trade fills (matched trades).

    Fills older than the historical cutoff are only available via get_historical_fills().

    Args:
        ticker: Optional market ticker filter
        limit:  Max fills per page (default 100, max 200)
        cursor: Pagination cursor from a previous response

    Returns: {fills: list, cursor: str | None}
    Each fill: {fill_id, ticker, side, action, count, yes_price, no_price, created_time}
    """
    c = _api()
    if not c:
        return _NO_CREDS
    params = {"limit": limit}
    if ticker:
        params["ticker"] = ticker
    if cursor:
        params["cursor"] = cursor
    r = c.get("/portfolio/fills", params=params)
    fills = [
        {
            "fill_id":      f.get("fill_id"),
            "order_id":     f.get("order_id"),
            "ticker":       f.get("ticker"),
            "side":         f.get("side"),
            "action":       f.get("action"),
            "count":        f.get("count"),
            "yes_price":    f.get("yes_price"),
            "no_price":     f.get("no_price"),
            "is_taker":     f.get("is_taker"),
            "created_time": f.get("created_time"),
        }
        for f in (r.get("fills") or [])
    ]
    return {"fills": fills, "cursor": r.get("cursor")}


# ---------------------------------------------------------------------------
# Historical Data
# ---------------------------------------------------------------------------
# Markets, fills, and orders older than the cutoff timestamps are only
# available via these /historical endpoints. Call get_historical_cutoff()
# first to know which date range requires historical queries.

def get_historical_cutoff() -> dict:
    """
    Get the current cutoff timestamps that partition live vs historical data.

    Returns:
        {
          market_settled_ts:  ISO timestamp — markets settled before this need /historical/markets
          trades_created_ts:  ISO timestamp — fills before this need /historical/fills
          orders_updated_ts:  ISO timestamp — orders before this need /historical/orders
        }
    """
    c = _api()
    if not c:
        return _NO_CREDS
    r = c.get("/historical/cutoff")
    return {
        "market_settled_ts": r.get("market_settled_ts"),
        "trades_created_ts": r.get("trades_created_ts"),
        "orders_updated_ts": r.get("orders_updated_ts"),
    }


def get_historical_markets(
    limit: int = 100,
    series_ticker: str = None,
    cursor: str = None,
) -> dict:
    """
    Get settled markets older than the market_settled_ts cutoff.

    Args:
        limit:         Max markets per page (default 100)
        series_ticker: Optional series filter (e.g. "KXNBA")
        cursor:        Pagination cursor from a previous response

    Returns: {markets: list, cursor: str | None}
    Each market: {ticker, event_ticker, title, status, close_time, settlement_value}
    """
    c = _api()
    if not c:
        return _NO_CREDS
    params: dict = {"limit": limit}
    if series_ticker:
        params["series_ticker"] = series_ticker
    if cursor:
        params["cursor"] = cursor
    r = c.get("/historical/markets", params=params)
    markets = [
        {
            "ticker":            m.get("ticker"),
            "event_ticker":      m.get("event_ticker"),
            "title":             m.get("title", ""),
            "status":            m.get("status"),
            "close_time":        m.get("close_time"),
            "settlement_value":  m.get("settlement_value"),
        }
        for m in (r.get("markets") or [])
    ]
    return {"markets": markets, "cursor": r.get("cursor")}


def get_historical_market(ticker: str) -> dict:
    """
    Get a single historical (settled) market by ticker.

    Returns: {ticker, event_ticker, title, status, close_time, settlement_value, ...}
    """
    c = _api()
    if not c:
        return _NO_CREDS
    r = c.get(f"/historical/markets/{ticker}")
    m = r.get("market", {})
    return {
        "ticker":           m.get("ticker"),
        "event_ticker":     m.get("event_ticker"),
        "title":            m.get("title", ""),
        "status":           m.get("status"),
        "close_time":       m.get("close_time"),
        "settlement_value": m.get("settlement_value"),
    }


def get_historical_candlesticks(
    ticker: str,
    start_ts: int = None,
    end_ts: int = None,
    period_interval: int = 60,
) -> dict:
    """
    Get OHLC candlestick data for a historical (settled) market.

    Args:
        ticker:          Market ticker
        start_ts:        Unix timestamp (seconds) for range start
        end_ts:          Unix timestamp (seconds) for range end
        period_interval: Candle size in minutes (default 60)

    Returns: {ticker, candles: [{ts, open, high, low, close, volume}, ...]}
    Prices in CENTS.
    """
    c = _api()
    if not c:
        return _NO_CREDS
    params: dict = {"period_interval": period_interval}
    if start_ts:
        params["start_ts"] = start_ts
    if end_ts:
        params["end_ts"] = end_ts
    r = c.get(f"/historical/markets/{ticker}/candlesticks", params=params)
    candles = [
        {
            "ts":     cs.get("end_period_ts"),
            "open":   cs.get("open"),
            "high":   cs.get("high"),
            "low":    cs.get("low"),
            "close":  cs.get("close"),
            "volume": cs.get("volume"),
        }
        for cs in (r.get("candlesticks") or [])
    ]
    return {"ticker": ticker, "candles": candles}


def get_historical_fills(
    ticker: str = None,
    limit: int = 100,
    cursor: str = None,
) -> dict:
    """
    Get your trade fills older than the trades_created_ts cutoff.

    Args:
        ticker: Optional market ticker filter
        limit:  Max fills per page (default 100)
        cursor: Pagination cursor from a previous response

    Returns: {fills: list, cursor: str | None}
    Each fill: {trade_id, ticker, side, action, count, yes_price, no_price, created_time}
    """
    c = _api()
    if not c:
        return _NO_CREDS
    params: dict = {"limit": limit}
    if ticker:
        params["ticker"] = ticker
    if cursor:
        params["cursor"] = cursor
    r = c.get("/historical/fills", params=params)
    fills = [
        {
            "trade_id":     f.get("trade_id"),
            "ticker":       f.get("ticker"),
            "side":         f.get("side"),
            "action":       f.get("action"),
            "count":        f.get("count"),
            "yes_price":    f.get("yes_price"),
            "no_price":     f.get("no_price"),
            "created_time": f.get("created_time"),
        }
        for f in (r.get("fills") or [])
    ]
    return {"fills": fills, "cursor": r.get("cursor")}


def get_historical_orders(
    ticker: str = None,
    limit: int = 100,
    cursor: str = None,
) -> dict:
    """
    Get your canceled/executed orders older than the orders_updated_ts cutoff.
    Note: resting (active) orders always appear in get_orders(), regardless of cutoff.

    Args:
        ticker: Optional market ticker filter
        limit:  Max orders per page (default 100)
        cursor: Pagination cursor from a previous response

    Returns: {orders: list, cursor: str | None}
    Each order: {order_id, ticker, side, action, type, yes_price, no_price,
                 remaining_count, status, created_time}
    """
    c = _api()
    if not c:
        return _NO_CREDS
    params: dict = {"limit": limit}
    if ticker:
        params["ticker"] = ticker
    if cursor:
        params["cursor"] = cursor
    r = c.get("/historical/orders", params=params)
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
    return {"orders": orders, "cursor": r.get("cursor")}
