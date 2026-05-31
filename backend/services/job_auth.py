"""
Per-user auth for scheduled jobs.

A scheduled run has no live request, so we store the user's Supabase **refresh
token** (long-lived, in the user_auth_tokens table) and exchange it for a fresh
access token at run time. The job then runs *as the user*, so authenticated
tools (portfolio, etc.) work.
"""
from typing import Optional

import httpx
from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert as pg_insert

from core.database import get_db_session
from models.user import UserAuthToken
from core.config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    """Upsert the user's refresh token."""
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


async def get_access_token(user_id: str) -> Optional[str]:
    """Exchange the stored refresh token for a fresh access token (rotating the
    stored refresh token). Returns None if unavailable — the job then runs with
    public tools only."""
    refresh = await _read_refresh(user_id)
    if not refresh:
        return None
    base = (settings.SUPABASE_URL or "").rstrip("/")
    apikey = settings.SUPABASE_SERVICE_KEY
    if not base or not apikey:
        return None
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{base}/auth/v1/token?grant_type=refresh_token",
                headers={"apikey": apikey, "Content-Type": "application/json"},
                json={"refresh_token": refresh},
            )
        if resp.status_code != 200:
            logger.warning(f"Token refresh for {user_id} failed: {resp.status_code}")
            return None
        data = resp.json()
        if data.get("refresh_token"):  # Supabase rotates the refresh token
            await store_refresh_token(user_id, data["refresh_token"])
        return data.get("access_token")
    except Exception as e:
        logger.error(f"Token refresh error for {user_id}: {e}")
        return None


async def has_token(user_id: str) -> bool:
    return (await _read_refresh(user_id)) is not None
