"""
Pydantic models for Skills API (kept for backward compat imports).

The canonical models are now defined inline in routes/skills.py.
"""
from pydantic import BaseModel
from typing import Optional


class SkillRequest(BaseModel):
    """Kept for backward compat — not used by catalog flow."""
    name: str
    description: str
    content: str
    enabled: bool = False


class SkillResponse(BaseModel):
    """Kept for backward compat — not used by catalog flow."""
    id: str
    name: str
    description: str
    content: str
    enabled: bool
    source_id: Optional[str] = None
    created_at: str
    updated_at: str
