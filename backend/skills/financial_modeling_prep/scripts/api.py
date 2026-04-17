"""Universal FMP API caller with in-memory TTL cache."""

import time
import json
from ._client import call_fmp_api, call_fmp_stable_api

# ─── Unified in-memory cache ──────────────────────────────────────────────────
# Every FMP call is cached by (endpoint, params) with a TTL based on data type.
# This dramatically reduces API calls and improves latency.

_cache: dict[str, tuple] = {}  # key -> (data, expires_at)
_MAX_ENTRIES = 1000

# TTL rules based on endpoint pattern
def _ttl_for(endpoint: str) -> int:
    ep = endpoint.lower()
    if '/quote/' in ep or ep.startswith('/quote'):
        return 30       # 30s — near real-time price data
    if '/profile/' in ep:
        return 3600     # 1h — company info rarely changes
    if '/search' in ep:
        return 300      # 5m — search results are stable
    if '/gainers' in ep or '/losers' in ep or '/actives' in ep:
        return 60       # 1m — movers change during market hours
    if '/stock_news' in ep or '/news' in ep:
        return 120      # 2m — news refreshes occasionally
    if '/earnings' in ep:
        return 3600     # 1h — calendar data
    if '/historical' in ep:
        return 300      # 5m — historical data
    return 60           # default 1m


def _cache_key(endpoint: str, params: dict | None) -> str:
    p = json.dumps(params, sort_keys=True) if params else ""
    return f"{endpoint}|{p}"


def _get(key: str):
    entry = _cache.get(key)
    if entry and entry[1] > time.time():
        return entry[0]
    return None


def _set(key: str, data, endpoint: str):
    _cache[key] = (data, time.time() + _ttl_for(endpoint))
    # Evict expired entries when cache grows large
    if len(_cache) > _MAX_ENTRIES:
        now = time.time()
        expired = [k for k, (_, exp) in _cache.items() if exp < now]
        for k in expired:
            del _cache[k]


def fmp(endpoint: str, params: dict | None = None):
    """
    Call any FMP API endpoint (cached).

    Args:
        endpoint: API path (e.g., '/profile/AAPL')
        params: Optional params (e.g., {'period': 'annual', 'limit': 5})

    Returns:
        dict or list: API response
    """
    key = _cache_key(endpoint, params)
    cached = _get(key)
    if cached is not None:
        return cached

    result = call_fmp_api(endpoint, params)

    # Don't cache errors
    if isinstance(result, dict) and result.get("error"):
        return result

    _set(key, result, endpoint)
    return result


def fmp_stable(endpoint: str, params: dict | None = None):
    """
    Call FMP Stable API endpoint (cached, uses /stable/ base).
    """
    key = _cache_key(f"stable:{endpoint}", params)
    cached = _get(key)
    if cached is not None:
        return cached

    result = call_fmp_stable_api(endpoint, params)

    if isinstance(result, dict) and result.get("error"):
        return result

    _set(key, result, endpoint)
    return result
