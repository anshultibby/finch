"""Pydantic schemas for user preferences."""
from typing import Optional
from pydantic import BaseModel, Field


class UserPreferences(BaseModel):
    """The user's current preferences (full set, defaults applied)."""
    require_trade_approval: bool = Field(
        True,
        description="When True, every real trade must go through review→approve. "
                    "When False, the agent may place orders unattended.",
    )
    morning_brief_enabled: bool = Field(
        False,
        description="When True, a daily morning brief (holdings + watchlist news) "
                    "is generated and delivered by email/push.",
    )
    morning_brief_time: str = Field(
        "08:00",
        description="Local delivery time for the morning brief, HH:MM.",
    )
    morning_brief_timezone: str = Field(
        "UTC",
        description="IANA timezone the brief time is interpreted in, e.g. Asia/Kolkata.",
    )
    morning_brief_phone: str = Field(
        "",
        description="E.164 WhatsApp number for brief delivery; empty disables WhatsApp.",
    )


class UpdatePreferencesRequest(BaseModel):
    """Partial update — only provided fields are changed."""
    require_trade_approval: Optional[bool] = None
    morning_brief_enabled: Optional[bool] = None
    morning_brief_time: Optional[str] = Field(None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    morning_brief_timezone: Optional[str] = Field(None, max_length=64)
    morning_brief_phone: Optional[str] = Field(None, pattern=r"^$|^\+[1-9]\d{6,14}$")
