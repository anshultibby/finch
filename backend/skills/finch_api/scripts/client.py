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


# ── Scheduled jobs ───────────────────────────────────────────────────────────

def schedule_job(message, run_at=None, in_minutes=None, recurrence=None,
                 name=None, priority=5, context_paths=None):
    """Schedule a one-off or recurring job that runs `message` at a future time.

    Provide either run_at (ISO-8601 UTC, e.g. '2026-06-01T13:30:00Z') OR
    in_minutes (relative). recurrence: None | 'hourly' | 'daily' | 'weekly' |
    'weekdays'. For an ALERT, make it recurring and have the message both check
    the condition AND notify only if it's met. Limits: 5 recurring + 10 one-off.
    """
    from datetime import datetime, timezone, timedelta
    if run_at is None:
        mins = in_minutes if in_minutes is not None else 60
        run_at = (datetime.now(timezone.utc) + timedelta(minutes=mins)).isoformat()
    body = {"message": message, "run_at": run_at, "recurrence": recurrence,
            "name": name, "priority": priority, "context_paths": context_paths or []}
    body = {k: v for k, v in body.items() if v is not None}
    return _request("POST", "/jobs", body=body)


def list_jobs():
    """List the user's scheduled jobs and how full their quota is."""
    return _request("GET", "/jobs")


def update_job(job_id, message=None, run_at=None, recurrence=None,
               clear_recurrence=False, name=None, priority=None):
    """Modify a scheduled job. Only provided fields change. Set
    clear_recurrence=True to turn a recurring job into a one-off."""
    body = {"message": message, "run_at": run_at, "recurrence": recurrence,
            "clear_recurrence": clear_recurrence, "name": name, "priority": priority}
    body = {k: v for k, v in body.items() if v is not None and not (k == "clear_recurrence" and v is False)}
    return _request("PATCH", f"/jobs/{job_id}", body=body)


def cancel_job(job_id):
    """Cancel a scheduled job by id."""
    return _request("DELETE", f"/jobs/{job_id}")


# ── Trade approval (one-click email) ─────────────────────────────────────────

def request_trade_approval(account_number, order_params, summary=None, ttl_minutes=60):
    """Stage a trade and email the user a one-click Approve/Reject link.

    Use this when an automation wants to place a real order but should NOT trade
    unattended: review the order first (review_order), then call this with the
    same order_params. The backend emails the user; if they click Approve, the
    backend places the order via the Robinhood MCP (you don't place it yourself).

    order_params mirrors the Robinhood order args (NO account_number — pass that
    separately): symbol, side, type, quantity|dollar_amount, limit_price, ...
    summary: a human-readable one-liner shown in the email (defaults to a basic
    one built from order_params). ttl_minutes: link lifetime, 5..1440 (default 60).

    Returns {token, status, expires_at, email_sent, summary}.
    """
    body = {"account_number": account_number, "order_params": order_params,
            "summary": summary, "ttl_minutes": ttl_minutes}
    body = {k: v for k, v in body.items() if v is not None}
    return _request("POST", "/trades/request-approval", body=body)


# ── Morning brief delivery ───────────────────────────────────────────────────

def send_morning_brief(subject, markdown, chat_id=None):
    """Deliver the user's morning brief by email + push notification.

    Use this from the morning-brief automation after composing the brief.
    subject: email subject / push title, e.g. "Finch brief: NVDA +4% pre-market".
    markdown: the full brief body (rendered to styled HTML for email).
    chat_id: optional — links the email CTA to that chat in the app.

    Returns {"email": bool, "push": bool} indicating what was delivered.
    """
    body = {"subject": subject, "markdown": markdown, "chat_id": chat_id}
    body = {k: v for k, v in body.items() if v is not None}
    return _request("POST", "/brief/send", body=body)
