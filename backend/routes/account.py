"""
Account management routes.

In-app account deletion is required by App Store Review Guideline 5.1.1(v):
an app that supports account creation must let the user initiate deletion of
their account (not just sign out) from within the app.
"""
from fastapi import APIRouter, Depends, HTTPException
from core.database import get_db_session
from core.config import Config
from auth.dependencies import get_current_user_id, verify_user_access
from schemas.preferences import UserPreferences, UpdatePreferencesRequest
from crud import user_preferences as prefs_crud
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/account", tags=["account"])


@router.get("/{user_id}/preferences", response_model=UserPreferences)
async def get_preferences(
    user_id: str,
    authenticated_user_id: str = Depends(get_current_user_id),
):
    """Return the user's preferences (defaults applied)."""
    await verify_user_access(user_id, authenticated_user_id)
    async with get_db_session() as db:
        return await prefs_crud.get_user_preferences(db, user_id)


@router.patch("/{user_id}/preferences", response_model=UserPreferences)
async def update_preferences(
    user_id: str,
    body: UpdatePreferencesRequest,
    authenticated_user_id: str = Depends(get_current_user_id),
):
    """Update one or more preferences (only provided fields change)."""
    await verify_user_access(user_id, authenticated_user_id)
    updates = body.model_dump(exclude_none=True)

    # Morning-brief settings drive a system job. Provision/retime/pause it
    # BEFORE persisting, so a bad timezone (or provisioning failure) rejects
    # the save instead of leaving the toggle on with no job behind it.
    if any(k.startswith("morning_brief") for k in updates):
        from services.system_jobs import configure_morning_brief
        async with get_db_session() as db:
            current = await prefs_crud.get_user_preferences(db, user_id)
        merged = {**current, **updates}
        try:
            await configure_morning_brief(
                user_id,
                enabled=merged["morning_brief_enabled"],
                time_str=merged["morning_brief_time"],
                tz_name=merged["morning_brief_timezone"],
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    async with get_db_session() as db:
        return await prefs_crud.update_user_preferences(db, user_id, updates)


@router.delete("/{user_id}")
async def delete_account(
    user_id: str,
    authenticated_user_id: str = Depends(get_current_user_id),
):
    """
    Permanently delete the authenticated user's account.

    Order matters: we best-effort purge application data first, then delete the
    Supabase auth user last. Deleting the auth user is the compliance-critical
    step — once it's gone the account can no longer sign in — so even if a
    data-cleanup step fails, the account is still effectively deleted.
    """
    await verify_user_access(user_id, authenticated_user_id)

    # 1. Best-effort: tear down external brokerage registrations so we don't
    #    leave dangling links at SnapTrade / Robinhood. Failures here must not
    #    block the deletion.
    try:
        from crud import snaptrade_user as snaptrade_crud
        async with get_db_session() as db:
            await snaptrade_crud.delete_user_async(db, user_id)
    except Exception as e:
        logger.warning(f"account delete: snaptrade cleanup failed for {user_id}: {e}")

    # 2. Best-effort: delete application data keyed by user_id.
    try:
        async with get_db_session() as db:
            from sqlalchemy import delete
            from models.user import UserAccount
            from models.chat_models import Chat

            await db.execute(delete(Chat).where(Chat.user_id == user_id))
            await db.execute(delete(UserAccount).where(UserAccount.user_id == user_id))
            await db.commit()
    except Exception as e:
        logger.warning(f"account delete: app-data cleanup failed for {user_id}: {e}")

    # 3. Compliance-critical: delete the Supabase auth user.
    if not (Config.SUPABASE_URL and Config.SUPABASE_SERVICE_KEY):
        raise HTTPException(status_code=500, detail="Account deletion is not configured")

    try:
        from supabase import create_client
        client = create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_KEY)
        client.auth.admin.delete_user(user_id)
    except Exception as e:
        logger.error(f"account delete: failed to delete auth user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete account. Please try again or contact support@finchapp.ai.")

    logger.info(f"Account deleted for user {user_id}")
    return {"success": True}
