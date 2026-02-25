"""
CRUD operations for skills
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update
from models.db import Skill, GlobalSkill
from typing import List, Optional
from uuid import uuid4


# ── User skills ──────────────────────────────────────────────────────────────

async def create_skill(
    db: AsyncSession,
    user_id: str,
    name: str,
    description: str,
    content: str,
    enabled: bool = True,
    source_id: Optional[str] = None,
) -> Skill:
    skill = Skill(
        id=str(uuid4()),
        user_id=user_id,
        name=name,
        description=description,
        content=content,
        enabled=enabled,
        source_id=source_id,
    )
    db.add(skill)
    await db.flush()
    return skill


async def get_user_skills(db: AsyncSession, user_id: str, enabled_only: bool = False) -> List[Skill]:
    query = select(Skill).where(Skill.user_id == user_id)
    if enabled_only:
        query = query.where(Skill.enabled == True)
    query = query.order_by(Skill.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_skill(db: AsyncSession, skill_id: str, user_id: str) -> Optional[Skill]:
    result = await db.execute(
        select(Skill).where(Skill.id == skill_id, Skill.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def update_skill(
    db: AsyncSession,
    skill_id: str,
    user_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    content: Optional[str] = None,
    enabled: Optional[bool] = None,
) -> Optional[Skill]:
    skill = await get_skill(db, skill_id, user_id)
    if not skill:
        return None
    if name is not None:
        skill.name = name
    if description is not None:
        skill.description = description
    if content is not None:
        skill.content = content
    if enabled is not None:
        skill.enabled = enabled
    await db.flush()
    return skill


async def delete_skill(db: AsyncSession, skill_id: str, user_id: str) -> bool:
    result = await db.execute(
        delete(Skill).where(Skill.id == skill_id, Skill.user_id == user_id)
    )
    return result.rowcount > 0


async def get_auto_skills(db: AsyncSession, user_id: str) -> List[Skill]:
    """Return skills that are always-on (enabled=True) for this user."""
    result = await db.execute(
        select(Skill).where(Skill.user_id == user_id, Skill.enabled == True)
        .order_by(Skill.created_at.desc())
    )
    return list(result.scalars().all())


async def is_already_installed(db: AsyncSession, user_id: str, source_id: str) -> bool:
    result = await db.execute(
        select(Skill.id).where(Skill.user_id == user_id, Skill.source_id == source_id)
    )
    return result.scalar_one_or_none() is not None


# ── Global skill store ────────────────────────────────────────────────────────

async def get_store_skills(
    db: AsyncSession,
    category: Optional[str] = None,
    official_only: bool = False,
) -> List[GlobalSkill]:
    query = select(GlobalSkill)
    if category:
        query = query.where(GlobalSkill.category == category)
    if official_only:
        query = query.where(GlobalSkill.is_official == True)
    query = query.order_by(GlobalSkill.is_official.desc(), GlobalSkill.install_count.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_global_skill(db: AsyncSession, skill_id: str) -> Optional[GlobalSkill]:
    result = await db.execute(select(GlobalSkill).where(GlobalSkill.id == skill_id))
    return result.scalar_one_or_none()


async def publish_skill(
    db: AsyncSession,
    name: str,
    description: str,
    content: str,
    category: Optional[str] = None,
    author_user_id: Optional[str] = None,
    is_official: bool = False,
) -> GlobalSkill:
    skill = GlobalSkill(
        id=str(uuid4()),
        name=name,
        description=description,
        content=content,
        category=category,
        author_user_id=author_user_id,
        is_official=is_official,
    )
    db.add(skill)
    await db.flush()
    return skill


async def install_skill(db: AsyncSession, user_id: str, global_skill_id: str) -> Optional[Skill]:
    """Copy a store skill into the user's library and bump install_count."""
    global_skill = await get_global_skill(db, global_skill_id)
    if not global_skill:
        return None

    # Bump install count
    await db.execute(
        update(GlobalSkill)
        .where(GlobalSkill.id == global_skill_id)
        .values(install_count=GlobalSkill.install_count + 1)
    )

    # Copy into user's library
    user_skill = await create_skill(
        db=db,
        user_id=user_id,
        name=global_skill.name,
        description=global_skill.description,
        content=global_skill.content,
        source_id=global_skill.id,
    )
    return user_skill
