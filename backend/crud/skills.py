"""
CRUD operations for user skills.

Skills themselves live on disk at backend/skills/<skill_name>/.
This module only manages the user's enabled/disabled preferences.
"""
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.user import UserSkill
from typing import List

_SKILLS_DIR = Path(__file__).parent.parent / "skills"


def _get_auto_on_skill_names() -> List[str]:
    """Return skill names that have auto_on: true in their SKILL.md frontmatter."""
    names = []
    if not _SKILLS_DIR.exists():
        return names
    for skill_dir in sorted(_SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir() or skill_dir.name.startswith("_"):
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        try:
            text = skill_md.read_text(encoding="utf-8")
            if "auto_on: true" in text:
                names.append(skill_dir.name)
        except Exception:
            continue
    return names


async def get_enabled_skill_names(db: AsyncSession, user_id: str) -> List[str]:
    """Return skill names that are enabled for this user.

    Always includes skills marked auto_on: true in their SKILL.md, plus any
    skills the user has explicitly enabled in the DB.
    """
    result = await db.execute(
        select(UserSkill.skill_name).where(
            UserSkill.user_id == user_id,
            UserSkill.enabled == True,
        )
    )
    user_enabled = set(result.scalars().all())
    auto_on = set(_get_auto_on_skill_names())
    return list(auto_on | user_enabled)


