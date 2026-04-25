"""ORATS API client — direct HTTP with token auth, gzip support, and DB cache."""
import os
import gzip
import json
import time
import hashlib
import urllib.request
import urllib.parse
import urllib.error
from typing import Any

BASE_URL = "https://api.orats.io/datav2"

# In-memory cache for current (non-historical) endpoints — short TTL
_mem_cache: dict[str, tuple] = {}
_MAX_MEM_ENTRIES = 200


def _cache_key(endpoint: str, params: dict) -> str:
    """Stable hash of endpoint + params (excluding token)."""
    params_no_token = {k: v for k, v in params.items() if k != "token"}
    raw = f"orats|{endpoint}|{json.dumps(params_no_token, sort_keys=True)}"
    return hashlib.md5(raw.encode()).hexdigest()


# ── DB cache (historical data — persists across restarts/deploys) ─────────────

def _db_get(key: str):
    try:
        from core.database import SessionLocal
        from sqlalchemy import text
        with SessionLocal() as db:
            row = db.execute(
                text("SELECT data FROM tool_cache WHERE cache_key = :key"),
                {"key": key}
            ).fetchone()
            return row[0] if row else None
    except Exception:
        return None


def _db_set(key: str, endpoint: str, params: dict, data: Any) -> None:
    try:
        from core.database import SessionLocal
        from sqlalchemy import text
        import json as _json
        params_no_token = {k: v for k, v in params.items() if k != "token"}
        with SessionLocal() as db:
            db.execute(text("""
                INSERT INTO tool_cache (cache_key, tool, endpoint, params, data, updated_at)
                VALUES (:key, 'orats', :endpoint, :params, :data, now())
                ON CONFLICT (cache_key) DO UPDATE
                SET data = EXCLUDED.data, updated_at = now()
            """), {
                "key": key,
                "endpoint": endpoint,
                "params": _json.dumps(params_no_token),
                "data": _json.dumps(data),
            })
            db.commit()
    except Exception:
        pass  # Cache write failure is non-fatal


# ── In-memory cache (current/live endpoints — 5 min TTL) ─────────────────────

def _mem_get(key: str):
    entry = _mem_cache.get(key)
    if entry and entry[1] > time.time():
        return entry[0]
    return None


def _mem_set(key: str, data: Any) -> None:
    _mem_cache[key] = (data, time.time() + 300)
    if len(_mem_cache) > _MAX_MEM_ENTRIES:
        now = time.time()
        for k in [k for k, (_, exp) in list(_mem_cache.items()) if exp < now]:
            del _mem_cache[k]


# ── Main caller ───────────────────────────────────────────────────────────────

def call_orats(endpoint: str, params: dict = None) -> Any:
    """
    Call any ORATS datav2 endpoint with automatic caching and gzip handling.

    Historical endpoints (hist/*) are cached to the DB permanently — they never
    change and each call returns years of data, so we never re-fetch them.
    Current endpoints are cached in-memory for 5 minutes.

    Args:
        endpoint: Path after /datav2/, e.g. 'strikes' or 'hist/ivrank'
        params:   Query params dict (token injected automatically)

    Returns:
        list: The 'data' array from ORATS response, or raises RuntimeError on failure.
    """
    token = os.getenv("ORATS_API_KEY")
    if not token:
        raise RuntimeError("ORATS_API_KEY is not set.")

    params = dict(params or {})
    params["token"] = token

    is_historical = endpoint.startswith("hist/")
    key = _cache_key(endpoint, params)

    # Check cache
    if is_historical:
        cached = _db_get(key)
        if cached is not None:
            return cached
    else:
        cached = _mem_get(key)
        if cached is not None:
            return cached

    # Fetch from API
    qs = urllib.parse.urlencode(params, doseq=True)
    url = f"{BASE_URL}/{endpoint}?{qs}"
    req = urllib.request.Request(url, headers={"Accept-Encoding": "identity", "User-Agent": "finch/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise RuntimeError(f"ORATS HTTP {e.code} on {endpoint}: {body}") from e

    try:
        data = json.loads(raw)
    except Exception:
        data = json.loads(gzip.decompress(raw))

    result = data.get("data", [])

    if is_historical:
        _db_set(key, endpoint, params, result)
    else:
        _mem_set(key, result)

    return result
