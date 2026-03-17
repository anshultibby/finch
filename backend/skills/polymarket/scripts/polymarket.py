"""
Polymarket market data — read-only HTTP helpers for all three Polymarket APIs.

No credentials required. All functions are synchronous.

Three API base URLs:
  GAMMA — events, markets, profiles, search (gamma-api.polymarket.com)
  CLOB  — orderbook, market trades (clob.polymarket.com)
  DATA  — leaderboard, trader positions/trades/activity, holders (data-api.polymarket.com)

Prices are floats in [0, 1] (e.g. 0.515 = 51.5¢).
"""
import json
import re
import urllib.request
import urllib.parse
import urllib.error

GAMMA_BASE = "https://gamma-api.polymarket.com"
CLOB_BASE = "https://clob.polymarket.com"
DATA_BASE = "https://data-api.polymarket.com"


def _http_get(url: str, params: dict = None) -> any:
    """Raw HTTP GET. Used internally by gamma(), clob(), data()."""
    query = ("?" + urllib.parse.urlencode(params, doseq=True)) if params else ""
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


def gamma(path: str, params: dict = None) -> any:
    """
    GET request to the Gamma API (gamma-api.polymarket.com).
    Events, markets, profiles, search.

    Example: gamma("/events", {"limit": 50, "active": "true", "tag_slug": "nba"})
    """
    return _http_get(f"{GAMMA_BASE}{path}", params)


def clob(path: str, params: dict = None) -> any:
    """
    GET request to the CLOB API (clob.polymarket.com).
    Orderbook data, market trades.

    Example: clob("/markets/CONDITION_ID")
    """
    return _http_get(f"{CLOB_BASE}{path}", params)


def data(path: str, params: dict = None) -> any:
    """
    GET request to the Data API (data-api.polymarket.com).
    Leaderboard, trader positions/trades/activity, holders.

    Example: data("/v1/leaderboard", {"category": "SPORTS", "timePeriod": "WEEK", "orderBy": "PNL", "limit": 25})
    """
    return _http_get(f"{DATA_BASE}{path}", params)


# ---------------------------------------------------------------------------
# Helpers for common quirks
# ---------------------------------------------------------------------------

def get_sport_events(sport: str, limit: int = 50) -> list:
    """
    Get active sports game markets. These are restricted=True and hidden from
    standard Gamma queries — this function paginates and filters for them.

    Args:
        sport: "nhl", "nba", "nfl", "mlb", "soccer", etc.
        limit: Max game events

    Returns: list of raw event dicts (with markets nested)
    """
    game_events = []
    batch_size = 100
    offset = 0

    while len(game_events) < limit:
        events = gamma("/events", {
            "tag_slug": sport,
            "limit": batch_size,
            "offset": offset,
            "active": "true",
            "closed": "false",
        })
        if not events:
            break
        for e in events:
            if e.get("restricted") and re.search(r"-\d{4}-\d{2}-\d{2}$", e.get("slug", "")):
                game_events.append(e)
        if len(events) < batch_size:
            break
        offset += batch_size

    return game_events[:limit]


def parse_outcomes(market: dict) -> dict:
    """
    Parse a Gamma market's outcomes and prices into {outcome_name: price_float}.

    The Gamma API returns outcomes and prices as JSON strings inside JSON.
    This helper decodes them.

    Example: parse_outcomes(market) → {"Red Wings": 0.515, "Predators": 0.485}
    """
    try:
        outcomes_raw = market.get("outcomes", "[]")
        prices_raw = market.get("outcomePrices", "[]")
        outcomes = json.loads(outcomes_raw) if isinstance(outcomes_raw, str) else outcomes_raw
        prices = json.loads(prices_raw) if isinstance(prices_raw, str) else prices_raw
        return {o: float(p) for o, p in zip(outcomes, prices)}
    except Exception:
        return {}
