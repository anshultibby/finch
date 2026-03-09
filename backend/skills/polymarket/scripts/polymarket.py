"""
Polymarket market data — event discovery, orderbook prices, trader leaderboards, and profiles.

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
DATA_BASE = "https://data-api.polymarket.com"


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
# Historical Data
# ---------------------------------------------------------------------------

def get_resolved_events(tag_slug: str = None, limit: int = 50) -> dict:
    """
    Get resolved/closed Polymarket events (markets that have already settled).

    Args:
        tag_slug: Category filter e.g. "nhl", "nba", "crypto", "politics"
        limit:    Max events to return

    Returns: {events: list, count: int}
    Each event: {id, slug, title, end_date, volume24hr, restricted, markets: [...]}
    Each market: {id, slug, question, outcomes, condition_id}
    Note: outcomes prices reflect final settled values (0.0 or 1.0 for binary markets).
    """
    params: dict = {"limit": limit, "closed": "true", "active": "false"}
    if tag_slug:
        params["tag_slug"] = tag_slug
    data = _get(f"{GAMMA_BASE}/events", params)
    return {"events": _parse_events(data), "count": len(data)}


def get_market_trades(condition_id: str, limit: int = 100) -> dict:
    """
    Get the public trade history for a market via the CLOB API.

    Args:
        condition_id: The market's condition_id
        limit:        Max trades to return (default 100)

    Returns: {condition_id, trades: list}
    Each trade: {id, outcome, price, size, timestamp}
    Prices are floats in [0, 1].
    """
    try:
        data = _get(f"{CLOB_BASE}/trades", params={"market": condition_id, "limit": limit})
        trades = [
            {
                "id":        t.get("id"),
                "outcome":   t.get("outcome"),
                "price":     float(t.get("price") or 0),
                "size":      float(t.get("size") or 0),
                "timestamp": t.get("timestamp"),
            }
            for t in (data if isinstance(data, list) else data.get("data", []))
        ]
        return {"condition_id": condition_id, "trades": trades}
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Leaderboard & Top Traders
# ---------------------------------------------------------------------------

def get_leaderboard(
    category: str = "OVERALL",
    time_period: str = "ALL",
    order_by: str = "PNL",
    limit: int = 25,
    offset: int = 0,
) -> dict:
    """
    Get the top traders leaderboard.

    Args:
        category:    OVERALL, POLITICS, SPORTS, CRYPTO, CULTURE, WEATHER, ECONOMICS, TECH, FINANCE
        time_period: DAY, WEEK, MONTH, ALL
        order_by:    PNL (profit/loss) or VOL (volume)
        limit:       Max traders (1-50)
        offset:      Pagination offset (0-1000)

    Returns: {traders: list}
    Each trader: {rank, proxy_wallet, username, pnl, volume, profile_image, x_username, verified}
    """
    params = {
        "category": category,
        "timePeriod": time_period,
        "orderBy": order_by,
        "limit": limit,
        "offset": offset,
    }
    try:
        data = _get(f"{DATA_BASE}/v1/leaderboard", params)
        traders = [
            {
                "rank":          t.get("rank"),
                "proxy_wallet":  t.get("proxyWallet"),
                "username":      t.get("userName"),
                "pnl":           float(t.get("pnl") or 0),
                "volume":        float(t.get("vol") or 0),
                "profile_image": t.get("profileImage"),
                "x_username":    t.get("xUsername"),
                "verified":      t.get("verifiedBadge", False),
            }
            for t in (data if isinstance(data, list) else [])
        ]
        return {"traders": traders, "count": len(traders)}
    except Exception as e:
        return {"error": str(e)}


def get_trader_profile(address: str) -> dict:
    """
    Get a trader's public profile by wallet address.

    Args:
        address: Wallet address (0x-prefixed, 40 hex chars)

    Returns: {name, pseudonym, bio, proxy_wallet, profile_image, x_username, verified, created_at}
    """
    try:
        data = _get(f"{GAMMA_BASE}/public-profile", params={"address": address})
        return {
            "name":          data.get("name"),
            "pseudonym":     data.get("pseudonym"),
            "bio":           data.get("bio"),
            "proxy_wallet":  data.get("proxyWallet"),
            "profile_image": data.get("profileImage"),
            "x_username":    data.get("xUsername"),
            "verified":      data.get("verifiedBadge", False),
            "created_at":    data.get("createdAt"),
        }
    except Exception as e:
        return {"error": str(e)}


def get_trader_positions(
    address: str,
    limit: int = 100,
    offset: int = 0,
    sort_by: str = "CURRENT",
    sort_direction: str = "DESC",
) -> dict:
    """
    Get a trader's current open positions.

    Args:
        address:        Wallet address (0x-prefixed)
        limit:          Max positions (0-500)
        offset:         Pagination offset
        sort_by:        CURRENT, INITIAL, TOKENS, CASHPNL, PERCENTPNL, TITLE, PRICE, AVGPRICE
        sort_direction: ASC or DESC

    Returns: {positions: list}
    Each position: {condition_id, title, outcome, size, avg_price, initial_value,
                    current_value, cash_pnl, percent_pnl, slug, event_slug}
    """
    params = {
        "user": address,
        "limit": limit,
        "offset": offset,
        "sortBy": sort_by,
        "sortDirection": sort_direction,
    }
    try:
        data = _get(f"{DATA_BASE}/positions", params)
        positions = [
            {
                "condition_id":  p.get("conditionId"),
                "title":         p.get("title"),
                "outcome":       p.get("outcome"),
                "size":          float(p.get("size") or 0),
                "avg_price":     float(p.get("avgPrice") or 0),
                "initial_value": float(p.get("initialValue") or 0),
                "current_value": float(p.get("currentValue") or 0),
                "cash_pnl":      float(p.get("cashPnl") or 0),
                "percent_pnl":   float(p.get("percentPnl") or 0),
                "slug":          p.get("slug"),
                "event_slug":    p.get("eventSlug"),
            }
            for p in (data if isinstance(data, list) else [])
        ]
        return {"positions": positions, "count": len(positions)}
    except Exception as e:
        return {"error": str(e)}


def get_trader_trades(
    address: str,
    limit: int = 100,
    offset: int = 0,
    market: str = None,
) -> dict:
    """
    Get a trader's trade history.

    Args:
        address: Wallet address (0x-prefixed)
        limit:   Max trades (0-10000)
        offset:  Pagination offset
        market:  Optional condition_id to filter to a specific market

    Returns: {trades: list}
    Each trade: {condition_id, title, outcome, side, price, size, timestamp, slug, event_slug}
    """
    params = {"user": address, "limit": limit, "offset": offset}
    if market:
        params["market"] = market
    try:
        data = _get(f"{DATA_BASE}/trades", params)
        trades = [
            {
                "condition_id": t.get("conditionId"),
                "title":        t.get("title"),
                "outcome":      t.get("outcome"),
                "side":         t.get("side"),
                "price":        float(t.get("price") or 0),
                "size":         float(t.get("size") or 0),
                "timestamp":    t.get("timestamp"),
                "slug":         t.get("slug"),
                "event_slug":   t.get("eventSlug"),
            }
            for t in (data if isinstance(data, list) else [])
        ]
        return {"trades": trades, "count": len(trades)}
    except Exception as e:
        return {"error": str(e)}


def get_trader_activity(
    address: str,
    limit: int = 100,
    offset: int = 0,
    activity_type: str = None,
) -> dict:
    """
    Get a trader's full activity feed (trades, splits, merges, redemptions, rewards).

    Args:
        address:       Wallet address (0x-prefixed)
        limit:         Max activities (0-500)
        offset:        Pagination offset
        activity_type: Optional filter: TRADE, SPLIT, MERGE, REDEEM, REWARD, CONVERSION, MAKER_REBATE

    Returns: {activities: list}
    Each activity: {type, condition_id, title, outcome, side, price, size, usdc_size, timestamp}
    """
    params = {"user": address, "limit": limit, "offset": offset}
    if activity_type:
        params["type"] = activity_type
    try:
        data = _get(f"{DATA_BASE}/activity", params)
        activities = [
            {
                "type":         a.get("type"),
                "condition_id": a.get("conditionId"),
                "title":        a.get("title"),
                "outcome":      a.get("outcome"),
                "side":         a.get("side"),
                "price":        float(a.get("price") or 0),
                "size":         float(a.get("size") or 0),
                "usdc_size":    float(a.get("usdcSize") or 0),
                "timestamp":    a.get("timestamp"),
                "slug":         a.get("slug"),
                "event_slug":   a.get("eventSlug"),
            }
            for a in (data if isinstance(data, list) else [])
        ]
        return {"activities": activities, "count": len(activities)}
    except Exception as e:
        return {"error": str(e)}


def get_market_holders(condition_id: str, limit: int = 20) -> dict:
    """
    Get top holders for a market (biggest position holders).

    Args:
        condition_id: The market's condition_id
        limit:        Max holders per outcome (1-20)

    Returns: {holders: list}
    Each entry: {token, holders: [{proxy_wallet, amount, pseudonym, name, profile_image}]}
    """
    try:
        data = _get(f"{DATA_BASE}/holders", params={"market": condition_id, "limit": limit})
        result = []
        for group in (data if isinstance(data, list) else []):
            holders = [
                {
                    "proxy_wallet":  h.get("proxyWallet"),
                    "amount":        float(h.get("amount") or 0),
                    "pseudonym":     h.get("pseudonym"),
                    "name":          h.get("name"),
                    "profile_image": h.get("profileImage"),
                }
                for h in (group.get("holders") or [])
            ]
            result.append({"token": group.get("token"), "holders": holders})
        return {"holders": result}
    except Exception as e:
        return {"error": str(e)}


def search_markets(query: str, limit: int = 10, include_profiles: bool = False) -> dict:
    """
    Search for markets, events, and optionally profiles.

    Args:
        query:            Search text
        limit:            Max results per type
        include_profiles: Also return matching trader profiles

    Returns: {events: list, profiles: list (if requested)}
    """
    params = {"q": query, "limit_per_type": limit}
    if include_profiles:
        params["search_profiles"] = "true"
    try:
        data = _get(f"{GAMMA_BASE}/public-search", params)
        result = {"events": _parse_events(data.get("events") or [])}
        if include_profiles:
            result["profiles"] = [
                {
                    "name":          p.get("name"),
                    "pseudonym":     p.get("pseudonym"),
                    "proxy_wallet":  p.get("proxyWallet"),
                    "profile_image": p.get("profileImage"),
                }
                for p in (data.get("profiles") or [])
            ]
        return result
    except Exception as e:
        return {"error": str(e)}


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
