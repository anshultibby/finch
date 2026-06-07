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


class UpdatePreferencesRequest(BaseModel):
    """Partial update — only provided fields are changed."""
    require_trade_approval: Optional[bool] = None
