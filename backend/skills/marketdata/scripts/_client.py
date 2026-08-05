"""MarketData.app API client — direct HTTP with Bearer auth, gzip support, and DB cache.

Real-time and historical options data with Greeks + IV. Response bodies are
*columnar* (parallel arrays keyed by field name); use `records_from()` to zip
them into a list of per-contract dicts.
"""
import os
import gzip
import json
import time
import hashlib
import urllib.request
import urllib.parse
import urllib.error
from typing import Any

BASE_URL = "https://api.marketdata.app"

# In-memory cache for live (non-dated) requests — short TTL
_mem_cache: dict[str, tuple] = {}
_MAX_MEM_ENTRIES = 200
_MEM_TTL = 60  # seconds — live quotes/greeks go stale fast


def _cache_key(endpoint: str, params: dict) -> str:
    """Stable hash of endpoint + params (token is never part of params here)."""
    raw = f"marketdata|{endpoint}|{json.dumps(params, sort_keys=True)}"
    return hashlib.md5(raw.encode()).hexdigest()


# ── DB cache (historical/dated data — immutable, persists across restarts) ─────

def _db_get(key: str):
    try:
        from core.database import SessionLocal
        from sqlalchemy import text
        with SessionLocal() as db:
            row = db.execute(
                text("SELECT data FROM tool_cache WHERE cache_key = :key"),
                {"key": key},
            ).fetchone()
            return row[0] if row else None
    except Exception:
        return None


def _db_set(key: str, endpoint: str, params: dict, data: Any) -> None:
    try:
        from core.database import SessionLocal
        from sqlalchemy import text
        with SessionLocal() as db:
            db.execute(text("""
                INSERT INTO tool_cache (cache_key, tool, endpoint, params, data, updated_at)
                VALUES (:key, 'marketdata', :endpoint, :params, :data, now())
                ON CONFLICT (cache_key) DO UPDATE
                SET data = EXCLUDED.data, updated_at = now()
            """), {
                "key": key,
                "endpoint": endpoint,
                "params": json.dumps(params),
                "data": json.dumps(data),
            })
            db.commit()
    except Exception:
        pass  # Cache write failure is non-fatal


# ── In-memory cache (live endpoints — short TTL) ──────────────────────────────

def _mem_get(key: str):
    entry = _mem_cache.get(key)
    if entry and entry[1] > time.time():
        return entry[0]
    return None


def _mem_set(key: str, data: Any) -> None:
    _mem_cache[key] = (data, time.time() + _MEM_TTL)
    if len(_mem_cache) > _MAX_MEM_ENTRIES:
        now = time.time()
        for k in [k for k, (_, exp) in list(_mem_cache.items()) if exp < now]:
            del _mem_cache[k]


# ── Response shaping ──────────────────────────────────────────────────────────

def records_from(data: dict, skip: tuple = ("s",)) -> list[dict]:
    """Zip a columnar MarketData response into a list of per-row dicts.

    MarketData returns parallel arrays (e.g. {"strike":[...], "delta":[...]}).
    This turns them into [{"strike":..., "delta":...}, ...].
    """
    if not isinstance(data, dict):
        return []
    list_keys = [k for k, v in data.items() if isinstance(v, list) and k not in skip]
    if not list_keys:
        return []
    n = len(data[list_keys[0]])
    return [{k: data[k][i] for k in list_keys} for i in range(n)]


# ── Main caller ───────────────────────────────────────────────────────────────

def _parse_body(raw: bytes) -> dict:
    """Parse a response body as JSON, transparently handling gzip."""
    try:
        return json.loads(raw)
    except Exception:
        return json.loads(gzip.decompress(raw))


def call_marketdata(endpoint: str, params: dict = None) -> dict:
    """Call any MarketData.app v1 endpoint with automatic caching and gzip handling.

    Dated requests (params contain `date`) are end-of-day snapshots that never
    change, so they're cached to the DB permanently. Live requests are cached
    in-memory for 60s.

    Args:
        endpoint: Path after the host, e.g. '/v1/options/chain/AAPL/'
        params:   Query params dict (token is injected via the auth header)

    Returns:
        dict: The parsed JSON response (columnar). `s` is 'ok' | 'no_data' | 'error'.
              Raises RuntimeError on transport error or an 'error' status.
    """
    token = os.getenv("MARKETDATA_API_KEY")
    if not token:
        raise RuntimeError("MARKETDATA_API_KEY is not set.")

    params = {k: v for k, v in (params or {}).items() if v is not None}
    is_dated = "date" in params
    key = _cache_key(endpoint, params)

    # Check cache
    cached = _db_get(key) if is_dated else _mem_get(key)
    if cached is not None:
        return cached

    qs = urllib.parse.urlencode(params, doseq=True)
    url = f"{BASE_URL}{endpoint}"
    if qs:
        url = f"{url}?{qs}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Accept-Encoding": "identity",
        "User-Agent": "finch/1.0",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as e:
        # MarketData signals "no data" with non-2xx codes (204/404) whose body is
        # still a normal JSON payload carrying an `s` status. Only treat it as a
        # hard error if the body isn't a MarketData status response.
        raw = e.read()
        data = _parse_body(raw)
        if not (isinstance(data, dict) and "s" in data):
            body = raw.decode(errors="replace")
            raise RuntimeError(f"MarketData HTTP {e.code} on {endpoint}: {body}") from e
    else:
        data = _parse_body(raw)

    status = data.get("s")
    if status == "error":
        raise RuntimeError(f"MarketData error on {endpoint}: {data.get('errmsg', data)}")

    if is_dated:
        _db_set(key, endpoint, params, data)
    else:
        _mem_set(key, data)

    return data
