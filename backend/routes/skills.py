"""
Skills API routes — user library + store
"""
from fastapi import APIRouter, HTTPException
from typing import Optional
from database import get_db_session
from crud import skills as skills_crud
from models.skills import SkillRequest, SkillResponse, GlobalSkillRequest, GlobalSkillResponse

router = APIRouter(prefix="/skills", tags=["skills"])


def _skill_out(skill) -> SkillResponse:
    return SkillResponse(
        id=skill.id,
        name=skill.name,
        description=skill.description,
        content=skill.content,
        enabled=skill.enabled,
        source_id=skill.source_id,
        created_at=skill.created_at.isoformat(),
        updated_at=skill.updated_at.isoformat(),
    )


def _global_skill_out(skill) -> GlobalSkillResponse:
    return GlobalSkillResponse(
        id=skill.id,
        name=skill.name,
        description=skill.description,
        content=skill.content,
        category=skill.category,
        is_official=skill.is_official,
        install_count=skill.install_count,
        author_user_id=skill.author_user_id,
        created_at=skill.created_at.isoformat(),
    )


# ── User library ──────────────────────────────────────────────────────────────

@router.get("/", response_model=list[SkillResponse])
async def list_skills(user_id: str, enabled_only: bool = False):
    async with get_db_session() as db:
        skills = await skills_crud.get_user_skills(db, user_id, enabled_only)
        return [_skill_out(s) for s in skills]


@router.post("/", response_model=SkillResponse)
async def create_skill(user_id: str, request: SkillRequest):
    async with get_db_session() as db:
        skill = await skills_crud.create_skill(
            db=db,
            user_id=user_id,
            name=request.name,
            description=request.description,
            content=request.content,
            enabled=request.enabled,
        )
        return _skill_out(skill)


@router.put("/{skill_id}", response_model=SkillResponse)
async def update_skill(skill_id: str, user_id: str, request: SkillRequest):
    async with get_db_session() as db:
        skill = await skills_crud.update_skill(
            db=db,
            skill_id=skill_id,
            user_id=user_id,
            name=request.name,
            description=request.description,
            content=request.content,
            enabled=request.enabled,
        )
        if not skill:
            raise HTTPException(status_code=404, detail="Skill not found")
        return _skill_out(skill)


@router.delete("/{skill_id}")
async def delete_skill(skill_id: str, user_id: str):
    async with get_db_session() as db:
        deleted = await skills_crud.delete_skill(db, skill_id, user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Skill not found")
        return {"message": "Skill deleted"}


# ── Store ─────────────────────────────────────────────────────────────────────

@router.get("/store", response_model=list[GlobalSkillResponse])
async def list_store_skills(category: Optional[str] = None, official_only: bool = False):
    async with get_db_session() as db:
        skills = await skills_crud.get_store_skills(db, category, official_only)
        return [_global_skill_out(s) for s in skills]


@router.post("/store", response_model=GlobalSkillResponse)
async def publish_to_store(user_id: str, request: GlobalSkillRequest):
    """Publish a skill to the store. Any user can contribute."""
    async with get_db_session() as db:
        skill = await skills_crud.publish_skill(
            db=db,
            name=request.name,
            description=request.description,
            content=request.content,
            category=request.category,
            author_user_id=user_id,
            is_official=False,
        )
        return _global_skill_out(skill)


@router.post("/store/{skill_id}/install", response_model=SkillResponse)
async def install_skill(skill_id: str, user_id: str):
    """Install a store skill into the user's library."""
    async with get_db_session() as db:
        # Check not already installed
        already = await skills_crud.is_already_installed(db, user_id, skill_id)
        if already:
            raise HTTPException(status_code=409, detail="Already installed")

        skill = await skills_crud.install_skill(db, user_id, skill_id)
        if not skill:
            raise HTTPException(status_code=404, detail="Store skill not found")
        return _skill_out(skill)
