"""
Per-user OAuth for Robinhood's agentic-trading MCP server.

Robinhood's MCP uses the standard MCP authorization flow:
OAuth 2.1 + PKCE (S256) + RFC 7591 dynamic client registration. No pre-arranged
credentials are required — Finch self-registers a *public* client (no secret) at
connect time, sends the user through Robinhood's hosted login/consent/funding
flow, then stores the resulting tokens (Fernet-encrypted, server-side only).

Flow:
  1. begin_connect(user_id)  -> registers a client, returns the authorize URL.
     The PKCE verifier + user_id + client_id are carried in a *signed* (Fernet-
     encrypted) `state` param, so nothing half-finished is persisted.
  2. Robinhood redirects the browser back to GET /robinhood/callback?code&state.
  3. complete_callback(code, state) -> exchanges the code, upserts the row.
  4. get_access_token(user_id) -> returns a fresh token, refreshing on demand.

Modeled on services/job_auth.py (refresh-token exchange) and the SnapTradeUser
connection pattern.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import urlencode

import httpx
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from core.config import settings
from core.database import get_db_session
from models.user import RobinhoodConnection
from services.encryption import encryption_service
from utils.logger import get_logger

logger = get_logger(__name__)

# Refresh a little before actual expiry to avoid races.
_EXPIRY_BUFFER = timedelta(seconds=60)


def _redirect_uri() -> str:
    return f"{settings.FINCH_BACKEND_URL.rstrip('/')}/robinhood/callback"


# ---------------------------------------------------------------------------
# PKCE + signed state
# ---------------------------------------------------------------------------

def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _new_pkce() -> tuple[str, str]:
    """Return (code_verifier, code_challenge) for PKCE S256."""
    verifier = _b64url(os.urandom(32))
    challenge = _b64url(hashlib.sha256(verifier.encode()).digest())
    return verifier, challenge


def _encode_state(payload: dict) -> str:
    """Sign+encrypt the OAuth state so it's tamper-proof and self-contained."""
    return encryption_service.encrypt(json.dumps(payload))


def _decode_state(state: str) -> Optional[dict]:
    try:
        return json.loads(encryption_service.decrypt(state))
    except Exception as e:
        logger.warning(f"Invalid Robinhood OAuth state: {e}")
        return None


# ---------------------------------------------------------------------------
# Dynamic client registration (RFC 7591)
# ---------------------------------------------------------------------------

async def _register_client() -> str:
    """Register a public OAuth client and return its client_id."""
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            settings.ROBINHOOD_OAUTH_REGISTRATION_URL,
            json={
                "client_name": "Finch",
                "redirect_uris": [_redirect_uri()],
                "grant_types": ["authorization_code", "refresh_token"],
                "response_types": ["code"],
                "token_endpoint_auth_method": "none",
            },
        )
    resp.raise_for_status()
    client_id = resp.json().get("client_id")
    if not client_id:
        raise RuntimeError("Robinhood DCR returned no client_id")
    return client_id


# ---------------------------------------------------------------------------
# Connect / callback
# ---------------------------------------------------------------------------

async def begin_connect(user_id: str) -> str:
    """Register a client and build the Robinhood authorize URL for this user."""
    client_id = await _register_client()
    verifier, challenge = _new_pkce()
    state = _encode_state({
        "user_id": user_id,
        "code_verifier": verifier,
        "client_id": client_id,
        "nonce": _b64url(os.urandom(9)),
    })
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": _redirect_uri(),
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "scope": settings.ROBINHOOD_OAUTH_SCOPE,
        "state": state,
        "resource": settings.ROBINHOOD_MCP_URL,  # RFC 8707 — required by Robinhood's MCP OAuth
    }
    return f"{settings.ROBINHOOD_OAUTH_AUTHORIZE_URL}?{urlencode(params)}"


async def exchange_native_code(user_id: str, code: str, code_verifier: str,
                               client_id: str, redirect_uri: str) -> None:
    """Exchange an auth code obtained by a NATIVE app (macOS/iOS) on-device via a
    loopback redirect, and persist the connection.

    The native app does DCR + PKCE + the loopback consent locally (the only flow
    Robinhood's agent client allows), then posts the resulting `code` here so the
    backend holds the tokens server-side — same storage the web callback uses."""
    token = await _token_request({
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "code_verifier": code_verifier,
    })
    await _store_tokens(user_id, client_id, token)


async def complete_callback(code: str, state: str) -> Optional[str]:
    """Exchange the auth code for tokens and persist the connection.

    Returns the user_id on success, or None if the state was invalid.
    """
    data = _decode_state(state)
    if not data:
        return None
    user_id = data["user_id"]
    client_id = data["client_id"]

    token = await _token_request({
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": _redirect_uri(),
        "client_id": client_id,
        "code_verifier": data["code_verifier"],
    })
    await _store_tokens(user_id, client_id, token)
    return user_id


async def _token_request(form: dict) -> dict:
    """POST to the OAuth token endpoint and return the parsed token response."""
    # RFC 8707 resource indicator — Robinhood's MCP OAuth requires it on every token
    # request (authorization_code AND refresh_token), bound to the MCP server URL.
    form.setdefault("resource", settings.ROBINHOOD_MCP_URL)
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            settings.ROBINHOOD_OAUTH_TOKEN_URL,
            data=form,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    if resp.status_code != 200:
        raise RuntimeError(f"Robinhood token endpoint {resp.status_code}: {resp.text}")
    return resp.json()


async def _store_tokens(user_id: str, client_id: str, token: dict) -> None:
    access = token.get("access_token")
    refresh = token.get("refresh_token")
    expires_in = int(token.get("expires_in", 3600))
    if not access:
        raise RuntimeError("Robinhood token response had no access_token")
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    values = {
        "user_id": user_id,
        "client_id": client_id,
        "encrypted_access_token": encryption_service.encrypt(access),
        "token_expires_at": expires_at,
        "is_connected": True,
    }
    # Robinhood may omit a new refresh token on refresh — keep the old one then.
    if refresh:
        values["encrypted_refresh_token"] = encryption_service.encrypt(refresh)

    async with get_db_session() as db:
        update_set = {k: v for k, v in values.items() if k != "user_id"}
        stmt = pg_insert(RobinhoodConnection.__table__).values(**values).on_conflict_do_update(
            index_elements=[RobinhoodConnection.user_id],
            set_=update_set,
        )
        await db.execute(stmt)
        await db.commit()


# ---------------------------------------------------------------------------
# Token access (with refresh) + status
# ---------------------------------------------------------------------------

async def _read_row(user_id: str) -> Optional[RobinhoodConnection]:
    async with get_db_session() as db:
        return (await db.execute(
            select(RobinhoodConnection).where(RobinhoodConnection.user_id == user_id)
        )).scalar_one_or_none()


async def get_access_token(user_id: str) -> Optional[str]:
    """Return a valid access token, refreshing via the refresh_token grant if the
    current one is expired/near-expiry. Returns None if the user isn't connected."""
    row = await _read_row(user_id)
    if not row or not row.is_connected or not row.encrypted_access_token:
        return None

    expires_at = row.token_expires_at
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at and expires_at - _EXPIRY_BUFFER > datetime.now(timezone.utc):
        return encryption_service.decrypt(row.encrypted_access_token)

    # Expired — refresh.
    if not row.encrypted_refresh_token:
        return encryption_service.decrypt(row.encrypted_access_token)
    try:
        token = await _token_request({
            "grant_type": "refresh_token",
            "refresh_token": encryption_service.decrypt(row.encrypted_refresh_token),
            "client_id": row.client_id,
        })
        await _store_tokens(user_id, row.client_id, token)
        return token.get("access_token")
    except Exception as e:
        logger.error(f"Robinhood token refresh failed for {user_id}: {e}")
        return None


async def is_connected(user_id: str) -> bool:
    row = await _read_row(user_id)
    return bool(row and row.is_connected and row.encrypted_access_token)


async def disconnect(user_id: str) -> None:
    """Clear the stored connection (revokes nothing on Robinhood's side)."""
    async with get_db_session() as db:
        row = (await db.execute(
            select(RobinhoodConnection).where(RobinhoodConnection.user_id == user_id)
        )).scalar_one_or_none()
        if row:
            row.is_connected = False
            row.encrypted_access_token = None
            row.encrypted_refresh_token = None
            row.token_expires_at = None
            await db.commit()


# ---------------------------------------------------------------------------
# Backend-side MCP call (used by the connected-account view)
# ---------------------------------------------------------------------------

def _parse_mcp_result(result: Any) -> Any:
    """Pull JSON/text out of an MCP CallToolResult into plain Python."""
    content = getattr(result, "content", None) or []
    for block in content:
        text = getattr(block, "text", None)
        if text is None:
            continue
        try:
            return json.loads(text)
        except (ValueError, TypeError):
            return text
    # Newer SDKs expose a parsed structuredContent.
    return getattr(result, "structuredContent", None)


async def mcp_call(user_id: str, tool: str, arguments: Optional[dict] = None) -> Any:
    """Call a single tool on the Robinhood MCP server as this user.

    Used by the backend for the connected-account view. Trading from the agent
    goes through the sandbox skill, not this helper.
    """
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    token = await get_access_token(user_id)
    if not token:
        raise RuntimeError("Robinhood is not connected for this user")

    headers = {"Authorization": f"Bearer {token}"}
    async with streamablehttp_client(settings.ROBINHOOD_MCP_URL, headers=headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool, arguments or {})
    return _parse_mcp_result(result)


def _f(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


async def _agentic_stats(user_id: str, account_number: str) -> dict:
    """Compute the live 'agent at work' stats for the connected-account view:
    today's P&L (positions × quotes), unrealized P&L, and recent activity."""
    positions_raw = await mcp_call(user_id, "get_equity_positions", {"account_number": account_number})
    positions = (positions_raw or {}).get("data", {}).get("positions", []) if isinstance(positions_raw, dict) else []
    held = [p for p in positions if _f(p.get("quantity")) > 0]

    # Quotes for held symbols → today's change + unrealized P&L.
    quotes: dict = {}
    if held:
        q_raw = await mcp_call(user_id, "get_equity_quotes", {"symbols": [p["symbol"] for p in held]})
        for r in (q_raw or {}).get("data", {}).get("results", []) if isinstance(q_raw, dict) else []:
            q = r.get("quote", {})
            if q.get("symbol"):
                quotes[q["symbol"]] = q

    today_amount = today_basis = unrealized = 0.0
    for p in held:
        q = quotes.get(p["symbol"])
        if not q:
            continue
        qty = _f(p.get("quantity"))
        last = _f(q.get("last_trade_price"))
        prev = _f(q.get("adjusted_previous_close"))
        today_amount += qty * (last - prev)
        today_basis += qty * prev
        unrealized += qty * (last - _f(p.get("average_buy_price")))

    today = None
    if today_basis > 0:
        today = {"amount": round(today_amount, 2), "pct": round(today_amount / today_basis * 100, 2)}

    # Recent activity from filled orders (newest first).
    orders_raw = await mcp_call(user_id, "get_equity_orders", {"account_number": account_number, "state": "filled"})
    orders = (orders_raw or {}).get("data", {}).get("orders", []) if isinstance(orders_raw, dict) else []
    last_trade = None
    if orders:
        o = orders[0]
        last_trade = {
            "side": o.get("side"), "symbol": o.get("symbol"),
            "quantity": o.get("quantity"), "price": o.get("average_price"),
            "at": o.get("last_transaction_at") or o.get("created_at"),
        }
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    trades_today = sum(1 for o in orders if str(o.get("created_at", "")).startswith(today_str))

    return {
        "today": today,
        "unrealized_pl": round(unrealized, 2) if held else None,
        "last_trade": last_trade,
        "trades_today": trades_today,
        "positions_count": len(held),
    }


async def get_agentic_portfolio(user_id: str) -> dict:
    """Full agentic-account view for the Agent tab: holdings (with live market value
    and unrealized P&L) + recent filled orders. Built from the same Robinhood MCP."""
    accounts_raw = await mcp_call(user_id, "get_accounts")
    accounts = (accounts_raw or {}).get("data", {}).get("accounts", []) if isinstance(accounts_raw, dict) else []
    agentic = next((a for a in accounts if a.get("agentic_allowed")), None)
    if not agentic:
        return {"agentic_account": None, "total_value": None, "buying_power": None, "holdings": [], "orders": []}
    acct = agentic["account_number"]

    total_value = buying_power = cash = None
    try:
        pf = (await mcp_call(user_id, "get_portfolio", {"account_number": acct}) or {}).get("data") or {}
        total_value = pf.get("total_value") or pf.get("market_value")
        bp = pf.get("buying_power")
        buying_power = bp.get("buying_power") if isinstance(bp, dict) else bp
        cash = pf.get("cash")
    except Exception as e:
        logger.warning(f"Robinhood get_portfolio failed for {user_id}: {e}")

    positions_raw = await mcp_call(user_id, "get_equity_positions", {"account_number": acct})
    positions = (positions_raw or {}).get("data", {}).get("positions", []) if isinstance(positions_raw, dict) else []
    held = [p for p in positions if _f(p.get("quantity")) > 0]

    quotes: dict = {}
    if held:
        q_raw = await mcp_call(user_id, "get_equity_quotes", {"symbols": [p["symbol"] for p in held]})
        for r in (q_raw or {}).get("data", {}).get("results", []) if isinstance(q_raw, dict) else []:
            q = r.get("quote", {})
            if q.get("symbol"):
                quotes[q["symbol"]] = q

    holdings = []
    for p in held:
        sym = p.get("symbol")
        q = quotes.get(sym, {})
        qty = _f(p.get("quantity"))
        avg = _f(p.get("average_buy_price"))
        last = _f(q.get("last_trade_price"))
        prev = _f(q.get("adjusted_previous_close"))
        holdings.append({
            "symbol": sym,
            "quantity": qty,
            "average_buy_price": round(avg, 2),
            "last_price": round(last, 2),
            "market_value": round(qty * last, 2),
            "unrealized_pl": round(qty * (last - avg), 2),
            "unrealized_pct": round((last - avg) / avg * 100, 2) if avg > 0 else 0.0,
            "today_pct": round((last - prev) / prev * 100, 2) if prev > 0 else 0.0,
        })
    holdings.sort(key=lambda h: h["market_value"], reverse=True)

    orders_raw = await mcp_call(user_id, "get_equity_orders", {"account_number": acct, "state": "filled"})
    orders_list = (orders_raw or {}).get("data", {}).get("orders", []) if isinstance(orders_raw, dict) else []
    orders = [{
        "side": o.get("side"),
        "symbol": o.get("symbol"),
        "quantity": o.get("quantity"),
        "price": o.get("average_price"),
        "at": o.get("last_transaction_at") or o.get("created_at"),
        "state": o.get("state"),
    } for o in orders_list[:200]]
    # The Agent tab reconstructs an equity curve from this fill history, so we keep
    # a deep slice (not just the few most-recent) — enough to reach the account's
    # start for a typical agent account.

    return {
        "agentic_account": agentic,
        "total_value": total_value,
        "buying_power": buying_power,
        "cash": cash,
        "holdings": holdings,
        "orders": orders,
    }


async def get_connected_accounts(user_id: str) -> dict:
    """Live snapshot for the UI: the agentic account + portfolio + agent stats."""
    accounts_raw = await mcp_call(user_id, "get_accounts")
    accounts = (accounts_raw or {}).get("data", {}).get("accounts", []) if isinstance(accounts_raw, dict) else []

    # Highlight the agent-enabled account and attach its live portfolio + stats.
    agentic = next((a for a in accounts if a.get("agentic_allowed")), None)
    portfolio = None
    stats = None
    if agentic:
        acct = agentic["account_number"]
        try:
            pf_raw = await mcp_call(user_id, "get_portfolio", {"account_number": acct})
            portfolio = (pf_raw or {}).get("data") if isinstance(pf_raw, dict) else None
        except Exception as e:
            logger.warning(f"Robinhood get_portfolio failed for {user_id}: {e}")
        try:
            stats = await _agentic_stats(user_id, acct)
        except Exception as e:
            logger.warning(f"Robinhood stats failed for {user_id}: {e}")

    return {"accounts": accounts, "agentic_account": agentic, "portfolio": portfolio, "stats": stats}
