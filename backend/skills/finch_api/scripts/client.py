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


def get_recent_trades(limit: int = 15) -> Dict[str, Any]:
    """The user's recent EXECUTED trades across their connected broker.

    Unified across Robinhood (filled orders) and SnapTrade (synced Transaction
    table); newest-first, each with a $ `amount` (qty×price) for size. Prefer
    this over get_transactions for "review my trades" — it covers Robinhood too
    and auto-syncs SnapTrade if the local table is empty.

    Returns {connected: bool, broker: str|None, trades: [
        {id, symbol, side, quantity, price, amount, date, broker}, ...]}.
    """
    return _request("GET", "/trades/recent", params={"limit": limit})


# ── Scheduled jobs ───────────────────────────────────────────────────────────

def schedule_job(message, run_at=None, in_minutes=None, recurrence=None, name=None):
    """Schedule an automation: a time to wake up, and an instruction to act on.

    Provide either run_at (ISO-8601 UTC, e.g. '2026-06-01T13:30:00Z') OR
    in_minutes (relative). recurrence: None | 'hourly' | 'daily' | 'weekly' |
    'weekdays'. For an ALERT, make it recurring and have the message both check
    the condition AND notify only if it's met. Limits: 5 recurring + 10 one-off.

    Each run executes in a fresh chat, so write anything the next run needs
    somewhere durable (a file, the journal, or report_insight).
    """
    from datetime import datetime, timezone, timedelta
    if run_at is None:
        mins = in_minutes if in_minutes is not None else 60
        run_at = (datetime.now(timezone.utc) + timedelta(minutes=mins)).isoformat()
    body = {"message": message, "run_at": run_at, "recurrence": recurrence, "name": name}
    body = {k: v for k, v in body.items() if v is not None}
    return _request("POST", "/jobs", body=body)


# Fields that answer "what is scheduled, when, and is it healthy?" — which is
# the only reason an agent lists jobs. Notably absent: `message`, the full
# instruction body, which for a trading automation runs to several hundred words
# per job and dominates the response.
_JOB_SUMMARY_FIELDS = (
    "id", "name", "run_at", "recurrence", "status",
    "last_run_at", "run_count", "last_error", "system_key",
)

_JOB_DONE_STATUSES = {"done", "failed", "cancelled"}


def list_jobs(active_only=True, include_message=False, message_chars=200):
    """List the user's scheduled jobs and how full their quota is.

    Returns a summary by default: id, name, run_at, recurrence, status, and
    run health — enough to decide "is tomorrow's wakeup already scheduled?",
    which is what this is almost always for.

    Deliberately NOT the full instruction bodies. Those are several hundred
    words each, and a finished automation accumulates dozens of rows, so the
    unfiltered response ran to ~19K tokens — then sat in context and got re-sent
    on every later call of the run.

        active_only     drop done/failed/cancelled rows (default True)
        include_message include instructions, truncated to message_chars
                        (pass message_chars=None for untruncated — rarely right)

    To read one job's full instruction, fetch it by id rather than listing.
    """
    result = _request("GET", "/jobs")
    jobs = result.get("jobs") or []

    if active_only:
        jobs = [j for j in jobs if j.get("status") not in _JOB_DONE_STATUSES]

    slim = []
    for j in jobs:
        row = {k: j[k] for k in _JOB_SUMMARY_FIELDS if k in j}
        if include_message:
            msg = j.get("message") or ""
            if message_chars is not None and len(msg) > message_chars:
                msg = msg[:message_chars] + "…"
            row["message"] = msg
        slim.append(row)

    return {**result, "jobs": slim}


def get_job(job_id):
    """One job in full, including its instruction body. Use this when you
    actually need to read or edit an instruction — not list_jobs()."""
    jobs = (_request("GET", "/jobs").get("jobs") or [])
    for j in jobs:
        if j.get("id") == job_id:
            return j
    return None


def update_job(job_id, message=None, run_at=None, recurrence=None,
               clear_recurrence=False, name=None):
    """Modify a scheduled job. Only provided fields change. Set
    clear_recurrence=True to turn a recurring job into a one-off."""
    body = {"message": message, "run_at": run_at, "recurrence": recurrence,
            "clear_recurrence": clear_recurrence, "name": name}
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


# ── Agent memory (heartbeat & friends) ───────────────────────────────────────

def list_events(limit=20, event_type=None):
    """Read the user's activity ledger — everything the agent has reported.

    This is your cross-run memory: heartbeat runs start in a fresh chat, so
    call this FIRST to see what you've already told the user and never repeat
    it. event_type filters to one kind: insight | alert | job_run |
    trade_proposed | trade_decided | brief.

    Returns {"events": [{event_type, title, body, data, created_at, ...}]}.
    """
    qs = f"?limit={int(limit)}"
    if event_type:
        qs += f"&event_type={event_type}"
    return _request("GET", f"/activity{qs}")


def search_past_chats(query, limit=10):
    """Content-search the user's past conversations (including automation runs).

    Use when the ledger isn't enough and you need deeper context — e.g.
    search_past_chats("GTLB thesis") to find what was said about a position.

    Returns {"results": [{chat_id, title, snippet, timestamp}]}.
    """
    import urllib.parse
    return _request("GET", f"/activity/search-chats?q={urllib.parse.quote(query)}&limit={int(limit)}")


# ── Agent insights (heartbeat & friends) ─────────────────────────────────────

def report_insight(title, body=None, alert=False, chat_id=None):
    """Report an insight to the user's activity ledger ("while you were gone").

    Use this from heartbeat/automation runs when you find something the user
    should know about their portfolio, watchlist, or the market.

    title: one punchy, specific line with numbers (<= 80 chars ideally).
    body: up to ~3 short supporting lines (optional).
    alert: True ALSO sends a push notification — reserve for urgent,
      decision-relevant items; a wrong alert erodes trust fast.
    chat_id: deep-links the insight/alert to a chat in the app. Defaults to
      the current run's chat (FINCH_CHAT_ID), so tapping it opens your work.

    Returns {"recorded": bool, "alerted": bool}.
    """
    import os
    if chat_id is None:
        chat_id = os.getenv("FINCH_CHAT_ID") or None
    payload = {"title": title, "body": body, "alert": alert, "chat_id": chat_id}
    payload = {k: v for k, v in payload.items() if v is not None}
    return _request("POST", "/activity/insight", body=payload)


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


# ── Trade ideas ──────────────────────────────────────────────────────────────

def propose_idea(symbol, catalyst_type, catalyst_summary, thesis,
                 entry_ref, stop, target, horizon_days=3, conviction=3,
                 bear_case=None, sources=None, direction="long"):
    """Propose a short-term, catalyst-driven trade idea for the user to decide on.

    The idea is recorded and scored on its horizon **whether or not the user
    approves it** — that's how we learn if the ideas are any good, separately
    from whether they got traded. So propose the ones you believe in and skip
    the ones you don't; a rejected idea still counts against your hit rate.

    Args:
      symbol:           ticker, e.g. "NVDA"
      catalyst_type:    earnings_beat | earnings_miss | guidance_raise |
                        guidance_cut | analyst_upgrade | analyst_downgrade |
                        m_and_a | fda | contract_win | product_launch |
                        legal_regulatory | insider_buying | index_inclusion |
                        macro | other
      catalyst_summary: the specific headline, QUOTED — not a paraphrase
      thesis:           why this moves the stock over the horizon
      entry_ref:        the price RIGHT NOW (from a tool call this run). This is
                        the scoring reference, not a fill.
      stop:             level that invalidates the thesis
      target:           where you'd take profit
      horizon_days:     1-15 trading days (default 3)
      conviction:       1-5 (bear_case is REQUIRED above 3)
      sources:          [{"title": ..., "url": ...}] backing the catalyst
      direction:        "long" (default) or "short"

    Levels must be ordered stop < entry_ref < target for a long (reversed for a
    short) or the call is rejected.

    Returns the created idea, including its id.
    """
    body = {"symbol": symbol, "catalyst_type": catalyst_type,
            "catalyst_summary": catalyst_summary, "thesis": thesis,
            "entry_ref": entry_ref, "stop": stop, "target": target,
            "horizon_days": horizon_days, "conviction": conviction,
            "bear_case": bear_case, "sources": sources or [],
            "direction": direction}
    body = {k: v for k, v in body.items() if v is not None}
    return _request("POST", "/ideas", body=body)


def list_ideas(limit=100):
    """List the user's trade ideas with the scorecard.

    Returns {"ideas": [...], "scorecard": {...}, "by_catalyst": {...}}.
    `scorecard` covers ALL ideas (traded or not): hit_rate, avg_return_pct,
    avg_alpha_pct (return over SPY — the number that matters), avg_r_multiple.
    `by_catalyst` breaks the same metrics down by catalyst_type, which tells you
    which catalysts actually work for this account. Read this before proposing:
    lean into the catalyst types that are earning alpha, drop the ones that aren't.
    """
    return _request("GET", "/ideas", params={"limit": limit})
