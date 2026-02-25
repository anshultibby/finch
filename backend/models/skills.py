"""
Pydantic models for Skills
"""
from pydantic import BaseModel, Field
from typing import Optional, List


class SkillRequest(BaseModel):
    """Request for creating/updating a user skill"""
    name: str = Field(..., min_length=1, max_length=64)
    description: str = Field(
        ..., min_length=1, max_length=1024,
        description="What the skill does AND when the agent should use it. "
                    "Both parts matter: the agent uses this to decide whether to load the skill."
    )
    content: str = Field(..., min_length=1)
    enabled: bool = Field(default=False)


class SkillResponse(BaseModel):
    """User skill response"""
    id: str
    name: str
    description: str
    content: str
    enabled: bool
    source_id: Optional[str] = None  # Set if installed from store
    created_at: str
    updated_at: str


class GlobalSkillRequest(BaseModel):
    """Request for publishing a skill to the store"""
    name: str = Field(..., min_length=1, max_length=64)
    description: str = Field(
        ..., min_length=1, max_length=1024,
        description="What the skill does AND when the agent should use it."
    )
    content: str = Field(..., min_length=1)
    category: Optional[str] = None


class GlobalSkillResponse(BaseModel):
    """Store skill response"""
    id: str
    name: str
    description: str
    content: str
    category: Optional[str]
    is_official: bool
    install_count: int
    author_user_id: Optional[str]
    created_at: str
