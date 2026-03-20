"""
Kalshi Trading — authenticated HTTP client for the Kalshi REST API.

Handles RSA-PS256 signing automatically. Call get/get_all/post/delete with any
Kalshi API path and get raw JSON responses.

Credentials from env vars:
  KALSHI_API_KEY_ID  — your Kalshi API key ID
  KALSHI_PRIVATE_KEY — RSA private key in PEM format
"""
from typing import Any
from ._client import create_client, _NO_CREDS

_client = None


def _api():
    global _client
    if _client is None:
        _client = create_client()
    return _client


def get(path: str, params: dict = None) -> Any:
    """
    Authenticated GET to any Kalshi API path.
    Example: get("/markets", {"limit": 100, "status": "open", "series_ticker": "KXNBA"})
    """
    c = _api()
    if not c:
        return _NO_CREDS
    return c.get(path, params=params)


def get_all(path: str, params: dict = None, collection_key: str = None, max_pages: int = 20) -> Any:
    """
    Auto-paginating GET. Fetches all pages and returns the merged list.

    Args:
        path: API path (e.g. "/events", "/markets", "/portfolio/positions")
        params: Query params. 'limit' defaults to 200 for /events, 1000 for /markets.
        collection_key: The JSON key containing the list (auto-detected from path if omitted).
        max_pages: Safety limit to prevent infinite loops (default 20).

    Returns the full list of items, or {"error": ...} on credential issues.

    Example:
        all_events = get_all("/events", {"status": "open", "with_nested_markets": True})
        all_markets = get_all("/markets", {"status": "open", "series_ticker": "KXNBAGAME"})
        positions = get_all("/portfolio/positions", {"count_filter": "position"})
    """
    c = _api()
    if not c:
        return _NO_CREDS

    params = dict(params or {})

    # Auto-detect collection key from path
    if collection_key is None:
        if "/multivariate_event_collections" in path:
            collection_key = "multivariate_contracts"
        elif "/events" in path:
            collection_key = "events"
        elif "/markets/trades" in path:
            collection_key = "trades"
        elif "/markets" in path:
            collection_key = "markets"
        elif "/positions" in path:
            collection_key = "market_positions"
        elif "/settlements" in path:
            collection_key = "settlements"
        elif "/orders" in path:
            collection_key = "orders"
        elif "/fills" in path:
            collection_key = "fills"
        elif "/milestones" in path:
            collection_key = "milestones"
        elif "/series" in path:
            collection_key = "series"
        else:
            collection_key = "items"

    # Exclude multivariate/combo markets by default on /markets
    # (MVE markets have near-zero liquidity and confuse game lookups)
    if "/markets" in path and "/multivariate" not in path:
        if "mve_filter" not in params:
            params["mve_filter"] = "exclude"

    # Set sensible default limit if not provided
    if "limit" not in params:
        params["limit"] = 1000 if "/markets" in path else 200

    all_items = []
    for _ in range(max_pages):
        r = c.get(path, params=params)
        if isinstance(r, dict) and "error" in r:
            return r
        items = r.get(collection_key, [])
        all_items.extend(items)
        cursor = r.get("cursor")
        if not cursor:
            break
        params["cursor"] = cursor

    return all_items


def post(path: str, body: Any = None) -> Any:
    """
    Authenticated POST to any Kalshi API path.
    Example: post("/portfolio/orders", {"ticker": "...", "side": "yes", "action": "buy", "count": 10, "type": "market"})
    """
    c = _api()
    if not c:
        return _NO_CREDS
    return c.post(path, body=body)


def delete(path: str) -> Any:
    """
    Authenticated DELETE to any Kalshi API path.
    Example: delete("/portfolio/orders/abc123")
    """
    c = _api()
    if not c:
        return _NO_CREDS
    return c.delete(path)
