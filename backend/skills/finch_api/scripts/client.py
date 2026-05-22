"""
Finch Backend API client for E2B sandbox.

Lets sandbox code call the backend directly using the injected
FINCH_API_URL, FINCH_AUTH_TOKEN, and FINCH_USER_ID env vars.
Data flows sandbox -> backend -> sandbox without touching agent context.
"""
import os
import json
import urllib.request
import urllib.error
import urllib.parse
from typing import Any, Dict, List, Optional


class FinchAPIError(Exception):
    def __init__(self, status: int, body: str):
        self.status = status
        self.body = body
        super().__init__(f"HTTP {status}: {body}")


class FinchAuthError(FinchAPIError):
    pass


class FinchConnectionError(Exception):
    pass


def _env(var: str) -> str:
    val = os.environ.get(var, "")
    if not val:
        raise RuntimeError(f"{var} is not set — this client only works inside the Finch sandbox")
    return val


def _request(
    method: str,
    path: str,
    params: Optional[Dict[str, Any]] = None,
    body: Optional[Any] = None,
    timeout: int = 30,
) -> Any:
    api_url = _env("FINCH_API_URL").rstrip("/")
    token = _env("FINCH_AUTH_TOKEN")
    user_id = _env("FINCH_USER_ID")

    params = dict(params or {})
    params.setdefault("user_id", user_id)
    # Drop None values
    params = {k: v for k, v in params.items() if v is not None}

    qs = urllib.parse.urlencode(params, doseq=True)
    url = f"{api_url}{path}?{qs}" if qs else f"{api_url}{path}"

    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "FinchSandbox/1.0",
    }

    if method.upper() in ("POST", "PUT", "PATCH") and body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    else:
        data = None
        if method.upper() == "POST" and body is None:
            data = b""

    req = urllib.request.Request(url, data=data, method=method.upper(), headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode(errors="replace")
        if e.code in (401, 403):
            raise FinchAuthError(e.code, body_text)
        raise FinchAPIError(e.code, body_text)
    except urllib.error.URLError as e:
        raise FinchConnectionError(f"Cannot reach backend at {api_url}: {e.reason}")


# ---------------------------------------------------------------------------
# Generic escape hatch
# ---------------------------------------------------------------------------

def finch_api(
    method: str,
    path: str,
    params: Optional[Dict[str, Any]] = None,
    body: Optional[Any] = None,
) -> Any:
    """Call any backend endpoint. Returns parsed JSON."""
    return _request(method, path, params=params, body=body)


# ---------------------------------------------------------------------------
# Convenience: transactions
# ---------------------------------------------------------------------------

def sync_transactions(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    force_resync: bool = False,
) -> Dict[str, Any]:
    """Trigger a server-side sync of brokerage transactions into the DB.

    Returns dict with transactions_fetched, transactions_inserted, etc.
    """
    params: Dict[str, Any] = {}
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    if force_resync:
        params["force_resync"] = "true"
    return _request("POST", "/api/analytics/transactions/sync", params=params, timeout=120)


def get_transactions(
    symbol: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """Fetch transactions from the DB (must sync first if data is stale).

    Returns list of transaction dicts with symbol, type, date, data, etc.
    """
    params: Dict[str, Any] = {"limit": limit}
    if symbol:
        params["symbol"] = symbol
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    result = _request("GET", "/api/analytics/transactions", params=params)
    return result.get("transactions", [])
