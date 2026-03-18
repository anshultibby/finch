"""
The Odds API client — fetch live odds, scores, and events for sports betting markets.

Uses only stdlib (runs inside E2B sandbox).
"""
import os
import json
import urllib.request
import urllib.error
import urllib.parse
from typing import Any, Dict, List, Optional


BASE_URL = "https://api.the-odds-api.com/v4"

# Track quota from response headers
_last_quota = {"remaining": None, "used": None}


def _request(path: str, params: Optional[Dict[str, Any]] = None) -> Any:
    """Make a GET request to The Odds API. Returns parsed JSON."""
    key = os.getenv("ODDS_API_KEY")
    if not key:
        return {"error": "ODDS_API_KEY is not set. Add it in Settings > API Keys."}

    cleaned = {k: v for k, v in (params or {}).items() if v is not None}
    cleaned["apiKey"] = key

    url = f"{BASE_URL}{path}?{urllib.parse.urlencode(cleaned, doseq=True)}"
    req = urllib.request.Request(url, headers={"User-Agent": "Finch/1.0"})

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            # Track quota
            _last_quota["remaining"] = resp.headers.get("x-requests-remaining")
            _last_quota["used"] = resp.headers.get("x-requests-used")
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        if e.code == 429:
            return {"error": "Rate limited — quota exceeded. Check get_quota()."}
        if e.code == 401:
            return {"error": "Invalid API key. Check ODDS_API_KEY."}
        raise RuntimeError(f"Odds API HTTP {e.code}: {body}") from e


def get_quota() -> Dict[str, Any]:
    """Return the last known API quota info from response headers."""
    return {
        "remaining": _last_quota["remaining"],
        "used": _last_quota["used"],
    }


# ── Sports ──────────────────────────────────────────────────────────────

def get_sports(all_sports: bool = False) -> List[Dict]:
    """
    List available sports. Free endpoint (no quota cost).

    Args:
        all_sports: If True, include out-of-season sports too.

    Returns list of {key, group, title, description, active, has_outrights}.
    """
    params = {}
    if all_sports:
        params["all"] = "true"
    return _request("/sports", params)


# ── Odds ────────────────────────────────────────────────────────────────

def get_odds(
    sport: str,
    regions: str = "us",
    markets: str = "h2h",
    odds_format: str = "american",
    bookmakers: Optional[str] = None,
    commence_time_from: Optional[str] = None,
    commence_time_to: Optional[str] = None,
) -> List[Dict]:
    """
    Get upcoming/live games with bookmaker odds.

    Args:
        sport: Sport key (e.g. "americanfootball_nfl", "basketball_nba").
        regions: Comma-separated regions: us, us2, uk, au, eu.
        markets: Comma-separated markets: h2h, spreads, totals, outrights.
        odds_format: "american" or "decimal".
        bookmakers: Optional comma-separated bookmaker keys to filter.
        commence_time_from: ISO 8601 start filter.
        commence_time_to: ISO 8601 end filter.

    Cost: 1 credit per region × market combo.
    """
    params = {
        "regions": regions,
        "markets": markets,
        "oddsFormat": odds_format,
    }
    if bookmakers:
        params["bookmakers"] = bookmakers
    if commence_time_from:
        params["commenceTimeFrom"] = commence_time_from
    if commence_time_to:
        params["commenceTimeTo"] = commence_time_to
    return _request(f"/sports/{sport}/odds", params)


def get_event_odds(
    sport: str,
    event_id: str,
    regions: str = "us",
    markets: str = "h2h,spreads,totals",
    odds_format: str = "american",
) -> Dict:
    """
    Get odds for a single event across all available markets.

    Args:
        sport: Sport key.
        event_id: Event ID from get_events() or get_odds().
        regions: Bookmaker regions.
        markets: Markets to fetch.
        odds_format: "american" or "decimal".
    """
    params = {
        "regions": regions,
        "markets": markets,
        "oddsFormat": odds_format,
    }
    return _request(f"/sports/{sport}/events/{event_id}/odds", params)


# ── Scores ──────────────────────────────────────────────────────────────

def get_scores(
    sport: str,
    days_from: Optional[int] = None,
    event_ids: Optional[str] = None,
) -> List[Dict]:
    """
    Get live and completed game scores.

    Args:
        sport: Sport key.
        days_from: Include completed games from past N days (1-3). Costs 2 credits instead of 1.
        event_ids: Optional comma-separated event IDs to filter.
    """
    params = {}
    if days_from:
        params["daysFrom"] = days_from
    if event_ids:
        params["eventIds"] = event_ids
    return _request(f"/sports/{sport}/scores", params)


# ── Events ──────────────────────────────────────────────────────────────

def get_events(
    sport: str,
    commence_time_from: Optional[str] = None,
    commence_time_to: Optional[str] = None,
    event_ids: Optional[str] = None,
) -> List[Dict]:
    """
    List events for a sport (no odds data). Free endpoint.

    Args:
        sport: Sport key.
        commence_time_from: ISO 8601 start filter.
        commence_time_to: ISO 8601 end filter.
        event_ids: Optional comma-separated event IDs.
    """
    params = {}
    if commence_time_from:
        params["commenceTimeFrom"] = commence_time_from
    if commence_time_to:
        params["commenceTimeTo"] = commence_time_to
    if event_ids:
        params["eventIds"] = event_ids
    return _request(f"/sports/{sport}/events", params)


def get_event_markets(
    sport: str,
    event_id: str,
) -> Dict:
    """
    List available market keys for an event by bookmaker.

    Args:
        sport: Sport key.
        event_id: Event ID.

    Cost: 1 credit.
    """
    return _request(f"/sports/{sport}/events/{event_id}/markets")


# ── Participants ────────────────────────────────────────────────────────

def get_participants(sport: str) -> List[Dict]:
    """
    List teams/participants for a sport.

    Cost: 1 credit.
    """
    return _request(f"/sports/{sport}/participants")
