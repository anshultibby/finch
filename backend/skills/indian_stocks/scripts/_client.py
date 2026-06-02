"""
Low-level client for the Indian Stock Market API (indianapi.in), for use inside
the E2B sandbox.

Auth is a header (``X-API-Key``), not a query param — so this skill talks to the
API directly rather than going through ``skills._shared._env.call_proxy`` (which
injects keys as query params for FMP/Polygon/Serper). The key is injected by the
backend as the ``INDIAN_API_KEY`` env var (see SKILL_ENV_KEYS in
modules/tools/skills_registry.py).

Base host is ``https://stock.indianapi.in``. (The docs site advertises
``analyst.indianapi.in``, but marketplace keys authenticate against the ``stock``
host.)
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional

BASE_URL = "https://stock.indianapi.in"
_TIMEOUT = 90  # the financials/historical endpoints can be slow


def _require_key() -> str:
    key = os.environ.get("INDIAN_API_KEY")
    if not key:
        raise RuntimeError(
            "INDIAN_API_KEY is not set — the Indian Stock Market API key is "
            "missing from the sandbox env. Check core/config.py + .env + "
            "SKILL_ENV_KEYS."
        )
    return key


def get(path: str, params: Optional[Dict[str, Any]] = None) -> Any:
    """GET an endpoint and return parsed JSON.

    path: e.g. "/stock" or "/stock_target_price"
    params: query params (None values are dropped)

    Returns the decoded JSON (dict or list). On HTTP error, returns
    ``{"error": "...", "status": <code>}`` so agent code never crashes mid-run.
    """
    clean = {k: v for k, v in (params or {}).items() if v is not None}
    url = BASE_URL + path
    if clean:
        url += "?" + urllib.parse.urlencode(clean)
    req = urllib.request.Request(
        url, headers={"X-API-Key": _require_key(), "User-Agent": "Finch/1.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        return {"error": body[:300], "status": e.code}
    except Exception as e:  # noqa: BLE001 — surface as data, don't crash the run
        return {"error": str(e)}
