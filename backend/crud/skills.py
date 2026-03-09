"""
CRUD operations for user skills.

Skills themselves live on disk at backend/skills/<skill_name>/.
This module only manages the user's enabled/disabled preferences.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from models.user import UserSkill
from typing import List, Optional
from uuid import uuid4


async def get_user_skills(db: AsyncSession, user_id: str) -> List[UserSkill]:
    """Return all UserSkill rows for this user."""
    result = await db.execute(
        select(UserSkill).where(UserSkill.user_id == user_id)
    )
    return list(result.scalars().all())


async def get_enabled_skill_names(db: AsyncSession, user_id: str) -> List[str]:
    """Return skill names that are enabled for this user."""
    result = await db.execute(
        select(UserSkill.skill_name).where(
            UserSkill.user_id == user_id,
            UserSkill.enabled == True,
        )
    )
    return list(result.scalars().all())


async def toggle_skill(
    db: AsyncSession,
    user_id: str,
    skill_name: str,
    enabled: bool,
) -> UserSkill:
    """Enable or disable a skill for a user. Upserts the row."""
    result = await db.execute(
        select(UserSkill).where(
            UserSkill.user_id == user_id,
            UserSkill.skill_name == skill_name,
        )
    )
    row = result.scalar_one_or_none()
    if row:
        row.enabled = enabled
    else:
        row = UserSkill(
            id=str(uuid4()),
            user_id=user_id,
            skill_name=skill_name,
            enabled=enabled,
        )
        db.add(row)
    await db.flush()
    return row


async def get_auto_skills(db: AsyncSession, user_id: str) -> List[UserSkill]:
    """Return skills that are always-on (enabled=True) for this user."""
    result = await db.execute(
        select(UserSkill).where(
            UserSkill.user_id == user_id,
            UserSkill.enabled == True,
        )
    )
    return list(result.scalars().all())
