"""
User preferences — small, safe key/value flags stored in UserSettings.settings
(JSONB), separate from the encrypted API-key blob. No migration needed.

Currently:
- require_trade_approval (bool, default True): when True the agent must route every
  real order through the review→approve flow (request_trade_approval). When False
  the user has opted into unattended trading and the agent may place_order directly
  (still bound by the day_trading RiskBudget / any dollar cap).
"""
from typing import Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession

from crud.user_api_keys import get_or_create_user_settings

# Whitelist of preference keys + their defaults. Only these are read/written via
# the preferences API, so arbitrary keys can't be injected into the settings blob.
DEFAULT_PREFERENCES: Dict[str, Any] = {
    "require_trade_approval": True,
    # Daily morning brief (delivered by the morning_brief system job —
    # provisioning is handled in routes/account.py on preference save).
    "morning_brief_enabled": False,
    "morning_brief_time": "08:00",       # HH:MM in the user's local timezone
    "morning_brief_timezone": "UTC",     # IANA name, e.g. Asia/Kolkata
    "morning_brief_phone": "",           # E.164 WhatsApp number, empty = off
}

_PREFS_KEY = "preferences"


async def get_user_preferences(db: AsyncSession, user_id: str) -> Dict[str, Any]:
    """Return the user's preferences merged over defaults."""
    settings = await get_or_create_user_settings(db, user_id)
    stored = (settings.settings or {}).get(_PREFS_KEY, {})
    prefs = dict(DEFAULT_PREFERENCES)
    for key in DEFAULT_PREFERENCES:
        if key in stored:
            prefs[key] = stored[key]
    return prefs


async def update_user_preferences(
    db: AsyncSession, user_id: str, updates: Dict[str, Any]
) -> Dict[str, Any]:
    """Merge whitelisted preference updates and persist. Returns the full set."""
    settings = await get_or_create_user_settings(db, user_id)
    current = dict((settings.settings or {}).get(_PREFS_KEY, {}))
    for key, value in updates.items():
        if key in DEFAULT_PREFERENCES and value is not None:
            current[key] = value
    # Reassign the whole JSONB dict so SQLAlchemy detects the change (matches the
    # existing api-keys persistence pattern).
    settings.settings = {**(settings.settings or {}), _PREFS_KEY: current}
    await db.commit()
    return await get_user_preferences(db, user_id)
