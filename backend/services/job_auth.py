"""
Per-user auth for scheduled jobs.

A scheduled run has no live request, so the backend needs its own credential
to act as the user. We mint a dedicated Supabase session with the admin API
(generate_link type=magiclink, then verify its hashed_token server-side — no
email is ever sent) and keep that session's refresh token in user_auth_tokens.

The minted session is its own refresh-token family, fully separate from the
user's browser/mobile sessions. That separation is the whole point: Supabase
rotates refresh tokens on use and revokes the entire family when a stale one
is replayed. The previous design spent the *browser's* refresh token here, so
every job run invalidated the copy still in the user's localStorage and logged
them out within the hour — most visibly right after each deploy, when the
scheduler caught up on due jobs. Never store a client-owned refresh token in
this table.
"""
import asyncio
import time
from typing import Dict, Optional, Tuple

import httpx
from sqlalchemy import delete, select, func
from sqlalchemy.dialects.postgresql import insert as pg_insert

from core.database import get_db_session
from models.user import UserAuthToken
from core.config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

# Access tokens live ~1h; serve them from memory so a burst of intraday job
# runs doesn't do a refresh-grant (and token rotation) per run. The lock
# serializes refresh/mint per user — two concurrent refreshes of the same
# token would trip Supabase's reuse detection and revoke our own family.
_ACCESS_CACHE_SLACK_S = 60
_access_cache: Dict[str, Tuple[str, float]] = {}  # user_id -> (token, expires_at)
_locks: Dict[str, asyncio.Lock] = {}


def _lock_for(user_id: str) -> asyncio.Lock:
    return _locks.setdefault(user_id, asyncio.Lock())


def _admin_headers() -> dict:
    key = settings.SUPABASE_SERVICE_KEY
    return {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}


async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    """Upsert the backend-owned refresh token for this user."""
    async with get_db_session() as db:
        stmt = pg_insert(UserAuthToken.__table__).values(
            user_id=user_id, refresh_token=refresh_token,
        ).on_conflict_do_update(
            index_elements=[UserAuthToken.user_id],
            set_={"refresh_token": refresh_token, "updated_at": func.now()},
        )
        await db.execute(stmt)
        await db.commit()


async def _read_refresh(user_id: str) -> Optional[str]:
    async with get_db_session() as db:
        row = (await db.execute(
            select(UserAuthToken.refresh_token).where(UserAuthToken.user_id == user_id)
        )).first()
        return row[0] if row else None


async def _drop_refresh(user_id: str) -> None:
    async with get_db_session() as db:
        await db.execute(delete(UserAuthToken.__table__).where(UserAuthToken.user_id == user_id))
        await db.commit()


async def _refresh_grant(client: httpx.AsyncClient, base: str, refresh: str) -> Tuple[Optional[dict], bool]:
    """Exchange our stored refresh token for a session.

    Returns (session, token_is_dead). A 4xx means the token is gone for good
    (rotated by another backend process / family revoked) — mint a new session
    instead of retrying.
    """
    resp = await client.post(
        f"{base}/auth/v1/token?grant_type=refresh_token",
        headers={"apikey": settings.SUPABASE_SERVICE_KEY, "Content-Type": "application/json"},
        json={"refresh_token": refresh},
    )
    if resp.status_code == 200:
        return resp.json(), False
    if 400 <= resp.status_code < 500:
        logger.info(f"Stored job refresh token rejected ({resp.status_code}); minting a new session")
        return None, True
    raise RuntimeError(f"refresh grant failed: {resp.status_code} {resp.text[:200]}")


async def _mint_session(client: httpx.AsyncClient, base: str, user_id: str) -> Optional[dict]:
    """Create a fresh backend-owned session for the user via the admin API.

    generate_link(type=magiclink) returns the OTP's hashed_token without
    sending any email; verifying it server-side yields a brand-new session
    (access + refresh token) in its own family.
    """
    resp = await client.get(f"{base}/auth/v1/admin/users/{user_id}", headers=_admin_headers())
    if resp.status_code != 200:
        logger.error(f"Admin user lookup for {user_id} failed: {resp.status_code} {resp.text[:200]}")
        return None
    email = resp.json().get("email")
    if not email:
        logger.error(f"User {user_id} has no email — cannot mint a job session")
        return None

    resp = await client.post(
        f"{base}/auth/v1/admin/generate_link",
        headers=_admin_headers(),
        json={"type": "magiclink", "email": email},
    )
    if resp.status_code != 200:
        logger.error(f"generate_link for {user_id} failed: {resp.status_code} {resp.text[:200]}")
        return None
    hashed_token = resp.json().get("hashed_token")
    if not hashed_token:
        logger.error(f"generate_link for {user_id} returned no hashed_token")
        return None

    resp = await client.post(
        f"{base}/auth/v1/verify",
        headers={"apikey": settings.SUPABASE_SERVICE_KEY, "Content-Type": "application/json"},
        json={"type": "magiclink", "token_hash": hashed_token},
    )
    if resp.status_code != 200:
        logger.error(f"verify for {user_id} failed: {resp.status_code} {resp.text[:200]}")
        return None
    return resp.json()


async def get_access_token(user_id: str) -> Optional[str]:
    """Access token for running jobs as this user. Served from cache while
    fresh; otherwise refreshes our stored session, minting a new one whenever
    the stored token is missing or dead. Returns None only on hard failure —
    the job then runs with public tools only."""
    base = (settings.SUPABASE_URL or "").rstrip("/")
    if not base or not settings.SUPABASE_SERVICE_KEY:
        return None

    async with _lock_for(user_id):
        cached = _access_cache.get(user_id)
        if cached and cached[1] - time.time() > _ACCESS_CACHE_SLACK_S:
            return cached[0]

        for attempt in range(3):  # retries cover network blips / 5xx only
            try:
                async with httpx.AsyncClient(timeout=15) as client:
                    session = None
                    refresh = await _read_refresh(user_id)
                    if refresh:
                        session, dead = await _refresh_grant(client, base, refresh)
                        if dead:
                            await _drop_refresh(user_id)
                    if session is None:
                        session = await _mint_session(client, base, user_id)
                    if session is None:
                        return None  # hard failure (no email, admin API rejected)

                    if session.get("refresh_token"):
                        await store_refresh_token(user_id, session["refresh_token"])
                    token = session.get("access_token")
                    if token:
                        expires_at = time.time() + int(session.get("expires_in") or 3600)
                        _access_cache[user_id] = (token, expires_at)
                    return token
            except Exception as e:
                logger.warning(f"Job token for {user_id}: {e} (attempt {attempt + 1}/3)")
            await asyncio.sleep(2 * (attempt + 1))
    return None


async def has_token(user_id: str) -> bool:
    """Whether jobs can run authenticated for this user. Sessions are minted
    on demand now, so this only requires Supabase admin to be configured."""
    return bool(settings.SUPABASE_URL and settings.SUPABASE_SERVICE_KEY)
