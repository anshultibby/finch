"""Pydantic schemas for the user's goal / "mission" (see models.user.UserGoal)."""
from datetime import date, datetime
from typing import Optional, Literal, Dict, Any
from pydantic import BaseModel, Field

GoalKind = Literal["number", "grow", "income", "protect"]


class Goal(BaseModel):
    """The user's active goal, as stored/returned."""
    kind: GoalKind = "number"
    title: str = ""
    objective: Optional[str] = None
    target_amount: Optional[float] = None
    deadline: Optional[date] = None
    horizon_years: Optional[int] = None
    monthly_contribution: Optional[float] = None
    monthly_income: Optional[float] = None
    risk: Optional[int] = Field(None, ge=1, le=10)
    options_enabled: bool = False
    config: Dict[str, Any] = Field(default_factory=dict)
    preferences: Dict[str, Any] = Field(default_factory=dict)
    status: str = "active"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class SetGoalRequest(BaseModel):
    """Full upsert of the user's goal from the onboarding wizard.

    Only `kind` is required; every shape-specific field is optional so a single
    endpoint serves all four goal types. Validators keep the numbers sane; the
    UI decides which fields are relevant for the chosen `kind`.
    """
    kind: GoalKind
    title: str = Field("", max_length=200)
    objective: Optional[str] = Field(None, max_length=1000)
    target_amount: Optional[float] = Field(None, ge=0, le=1_000_000_000)
    deadline: Optional[date] = None
    horizon_years: Optional[int] = Field(None, ge=1, le=60)
    monthly_contribution: Optional[float] = Field(None, ge=0, le=10_000_000)
    monthly_income: Optional[float] = Field(None, ge=0, le=10_000_000)
    risk: Optional[int] = Field(None, ge=1, le=10)
    options_enabled: bool = False
    config: Dict[str, Any] = Field(default_factory=dict)
    preferences: Dict[str, Any] = Field(default_factory=dict)
