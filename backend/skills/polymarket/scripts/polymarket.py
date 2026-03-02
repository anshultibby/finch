"""
Polymarket market data — event discovery and orderbook prices.

All functions are synchronous. Do not await them.

No credentials required for read-only market data.

KEY QUIRK: Sports game markets are tagged restricted=True (US geo-restriction).
They do NOT appear in standard tag queries unless you pass restricted=True.
Always use get_sport_events() for game-level markets, not get_events().

Prices are floats in [0, 1] (e.g. 0.515 = 51.5¢).
"""
import json
import urllib.request
import urllib.parse
import urllib.error
from typing import Optional

GAMMA_BASE = "https://gamma-api.polymarket.com"
CLOB_BASE = "https://clob.polymarket.com"


def _get(url: str, params: dict = None) -> any:
    query = ("?" + urllib.parse.urlencode(params)) if params else ""
    req = urllib.request.Request(
        url + query,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {body}") from e


# ---------------------------------------------------------------------------
# Event discovery
# ---------------------------------------------------------------------------

def get_events(tag_slug: str = None, limit: int = 50, active: bool = True) -> dict:
    """
    Get non-restricted Polymarket events (futures, politics, etc.).

    Args:
        tag_slug: Category filter e.g. "crypto", "politics", "sports"
        limit:    Max events to return
        active:   Only active (not yet resolved) events

    Returns: {events: list, count: int}
    Each event: {id, slug, title, volume24hr, liquidity, end_date, markets: [...]}
    Each market: {id, slug, question, outcomes, prices, condition_id}
    """
    params = {"limit": limit}
    if tag_slug:
        params["tag_slug"] = tag_slug
    if active:
        params["active"] = "true"
        params["closed"] = "false"

    data = _get(f"{GAMMA_BASE}/events", params)
    return {"events": _parse_events(data), "count": len(data)}


def get_sport_events(sport: str, limit: int = 50) -> dict:
    """
    Get active sports GAME markets (these are restricted=True and hidden from
    standard queries — this function handles that automatically).

    Paginates until it finds enough game-level events (identified by date slug suffix).

    Args:
        sport:  Sport slug: "nhl", "nba", "nfl", "mlb", "soccer", etc.
        limit:  Max game events to return

    Returns: {events: list, count: int}
    Each event: {id, slug, title, volume24hr, liquidity, end_date, markets: [...]}
    Each market: {id, slug, question, outcomes: {TeamA: price, TeamB: price}, condition_id}

    Slug format for game events: "{sport}-{away}-{home}-{yyyy}-{mm}-{dd}"
    e.g. "nhl-det-nsh-2026-03-02"
    """
    game_events = []
    batch_size = 100
    offset = 0

    while len(game_events) < limit:
        params = {
            "tag_slug": sport,
            "limit": batch_size,
            "offset": offset,
            "active": "true",
            "closed": "false",
        }
        data = _get(f"{GAMMA_BASE}/events", params)
        if not data:
            break
        for e in data:
            if e.get("restricted") and _looks_like_game(e.get("slug", "")):
                game_events.append(e)
        if len(data) < batch_size:
            break
        offset += batch_size

    game_events = game_events[:limit]
    return {"events": _parse_events(game_events), "count": len(game_events)}


def get_event(slug: str) -> dict:
    """
    Get a single event by slug.

    Args:
        slug: Event slug e.g. "nhl-det-nsh-2026-03-02"

    Returns: event dict with markets, or {"error": "..."}
    """
    try:
        data = _get(f"{GAMMA_BASE}/events", params={"slug": slug})
        if not data:
            return {"error": f"Event not found: {slug}"}
        events = _parse_events(data)
        return events[0] if events else {"error": f"Event not found: {slug}"}
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# CLOB (orderbook) data
# ---------------------------------------------------------------------------

def get_orderbook(condition_id: str) -> dict:
    """
    Get live orderbook for a market via the CLOB API.

    Args:
        condition_id: The market's condition_id (from get_sport_events or get_event)

    Returns: {condition_id, question, outcomes: {name: price}, bids, asks, accepting_orders}
    """
    try:
        data = _get(f"{CLOB_BASE}/markets/{condition_id}")
        tokens = data.get("tokens", [])
        return {
            "condition_id":      data.get("condition_id"),
            "question":          data.get("question"),
            "slug":              data.get("market_slug"),
            "outcomes":          {t["outcome"]: t["price"] for t in tokens},
            "accepting_orders":  data.get("accepting_orders", False),
            "min_order_size":    data.get("minimum_order_size"),
            "game_start_time":   data.get("game_start_time"),
        }
    except Exception as e:
        return {"error": str(e)}


def get_prices(condition_id: str) -> dict:
    """
    Get just the current mid-market prices for a market.

    Args:
        condition_id: The market's condition_id

    Returns: {outcome_name: price_float, ...}  e.g. {"Red Wings": 0.515, "Predators": 0.485}
    """
    ob = get_orderbook(condition_id)
    if "error" in ob:
        return ob
    return ob.get("outcomes", {})


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _looks_like_game(slug: str) -> bool:
    """Heuristic: game slugs have a date suffix like -2026-03-02."""
    import re
    return bool(re.search(r"-\d{4}-\d{2}-\d{2}$", slug))


def _parse_events(raw: list) -> list:
    out = []
    for e in raw:
        markets = []
        for m in (e.get("markets") or []):
            try:
                outcomes_raw = m.get("outcomes", "[]")
                prices_raw = m.get("outcomePrices", "[]")
                outcomes = json.loads(outcomes_raw) if isinstance(outcomes_raw, str) else outcomes_raw
                prices = json.loads(prices_raw) if isinstance(prices_raw, str) else prices_raw
                outcome_map = {o: float(p) for o, p in zip(outcomes, prices)}
            except Exception:
                outcome_map = {}
            markets.append({
                "id":           m.get("id"),
                "slug":         m.get("slug"),
                "question":     m.get("question"),
                "condition_id": m.get("conditionId"),
                "outcomes":     outcome_map,
                "volume":       float(m.get("volume") or 0),
                "liquidity":    float(m.get("liquidity") or 0),
            })
        out.append({
            "id":         e.get("id"),
            "slug":       e.get("slug"),
            "title":      e.get("title"),
            "end_date":   e.get("endDate", "")[:10],
            "volume24hr": float(e.get("volume24hr") or 0),
            "liquidity":  float(e.get("liquidity") or 0),
            "restricted": e.get("restricted", False),
            "markets":    markets,
        })
    return out
