"""
Apple Sign In with Apple server-to-server notifications.

Apple POSTs a signed JWT here when users change email forwarding preferences,
delete their app account, or permanently delete their Apple ID.

Docs: https://developer.apple.com/documentation/sign_in_with_apple/processing_changes_for_sign_in_with_apple_accounts
"""
import json
import httpx
import jwt
from jwt.algorithms import RSAAlgorithm
from fastapi import APIRouter, Request, HTTPException
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/auth/apple", tags=["auth"])

APPLE_JWKS_URL = "https://appleid.apple.com/auth/keys"
APPLE_ISSUER = "https://appleid.apple.com"
APPLE_AUDIENCE = "ai.finchapp.mobile"

_jwks_cache: dict | None = None


async def _get_apple_public_keys() -> dict:
    global _jwks_cache
    if _jwks_cache is not None:
        return _jwks_cache
    async with httpx.AsyncClient() as client:
        resp = await client.get(APPLE_JWKS_URL, timeout=10)
        resp.raise_for_status()
    _jwks_cache = resp.json()
    return _jwks_cache


async def _verify_apple_jwt(token: str) -> dict:
    """Verify Apple's signed notification JWT and return its payload."""
    header = jwt.get_unverified_header(token)
    kid = header.get("kid")

    jwks = await _get_apple_public_keys()
    key_data = next((k for k in jwks["keys"] if k["kid"] == kid), None)
    if key_data is None:
        # Key not found — maybe Apple rotated keys; bust the cache and retry once.
        global _jwks_cache
        _jwks_cache = None
        jwks = await _get_apple_public_keys()
        key_data = next((k for k in jwks["keys"] if k["kid"] == kid), None)
        if key_data is None:
            raise HTTPException(status_code=400, detail="Unknown Apple key id")

    public_key = RSAAlgorithm.from_jwk(json.dumps(key_data))
    return jwt.decode(
        token,
        public_key,
        algorithms=["RS256"],
        issuer=APPLE_ISSUER,
        audience=APPLE_AUDIENCE,
    )


async def _handle_account_delete(apple_user_id: str) -> None:
    """Delete the Finch account linked to this Apple user ID."""
    from core.config import Config
    from core.database import get_db_session
    from sqlalchemy import text

    if not (Config.SUPABASE_URL and Config.SUPABASE_SERVICE_KEY):
        logger.error("apple s2s: account-delete: Supabase not configured")
        return

    # Look up the Supabase user whose Apple provider sub matches.
    try:
        from supabase import create_client
        admin = create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_KEY)
        # list_users paginates; Apple user IDs are stored as the provider sub.
        page = 1
        user_id = None
        while True:
            response = admin.auth.admin.list_users(page=page, per_page=1000)
            users = response if isinstance(response, list) else response.users
            for u in users:
                for identity in (u.identities or []):
                    if identity.provider == "apple" and identity.id == apple_user_id:
                        user_id = u.id
                        break
                if user_id:
                    break
            if user_id or len(users) < 1000:
                break
            page += 1
    except Exception as e:
        logger.error(f"apple s2s: account-delete: failed to look up user {apple_user_id}: {e}")
        return

    if not user_id:
        logger.warning(f"apple s2s: account-delete: no Finch account for Apple sub {apple_user_id}")
        return

    logger.info(f"apple s2s: account-delete: deleting Finch account {user_id} (Apple sub {apple_user_id})")

    # Reuse the same cleanup logic as DELETE /account/{user_id}.
    try:
        from crud import snaptrade_user as snaptrade_crud
        async with get_db_session() as db:
            await snaptrade_crud.delete_user_async(db, user_id)
    except Exception as e:
        logger.warning(f"apple s2s: account-delete: snaptrade cleanup failed: {e}")

    try:
        async with get_db_session() as db:
            from sqlalchemy import delete
            from models.user import UserAccount
            from models.chat_models import Chat
            await db.execute(delete(Chat).where(Chat.user_id == user_id))
            await db.execute(delete(UserAccount).where(UserAccount.user_id == user_id))
            await db.commit()
    except Exception as e:
        logger.warning(f"apple s2s: account-delete: app-data cleanup failed: {e}")

    try:
        admin.auth.admin.delete_user(user_id)
        logger.info(f"apple s2s: account-delete: auth user {user_id} deleted")
    except Exception as e:
        logger.error(f"apple s2s: account-delete: failed to delete auth user {user_id}: {e}")


@router.post("/notifications")
async def apple_notifications(request: Request):
    """
    Receive Sign in with Apple server-to-server notifications.
    Apple sends a form-encoded `payload` field containing a signed JWT.
    """
    form = await request.form()
    token = form.get("payload")
    if not token:
        raise HTTPException(status_code=400, detail="Missing payload")

    try:
        claims = await _verify_apple_jwt(str(token))
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=400, detail="Expired notification JWT")
    except jwt.InvalidTokenError as e:
        logger.warning(f"apple s2s: invalid JWT: {e}")
        raise HTTPException(status_code=400, detail="Invalid notification JWT")

    # `events` is a JSON string inside the JWT claims.
    try:
        events_raw = claims.get("events", "{}")
        event = json.loads(events_raw) if isinstance(events_raw, str) else events_raw
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Malformed events payload")

    event_type = event.get("type")
    apple_sub = event.get("sub")  # Apple user ID
    logger.info(f"apple s2s: received event={event_type} sub={apple_sub}")

    if event_type == "account-delete" and apple_sub:
        await _handle_account_delete(apple_sub)
    elif event_type in ("email-disabled", "email-enabled"):
        # Email forwarding preference changed — no action required on our side.
        pass
    elif event_type == "consent-revoked":
        # User revoked consent — treat the same as account deletion.
        if apple_sub:
            await _handle_account_delete(apple_sub)
    else:
        logger.info(f"apple s2s: unhandled event type '{event_type}'")

    return {"ok": True}
