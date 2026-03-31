"""
Skills API routes.

Skills live on disk at backend/skills/<name>/. This API:
- Lists available skills with their metadata (read from SKILL.md frontmatter)
- Exposes file contents for the UI browser
- Manages per-user enabled/disabled state in DB (UserSkill table)
"""
from fastapi import APIRouter, HTTPException
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel
import re

from core.database import get_db_session
from crud import skills as skills_crud

router = APIRouter(prefix="/skills", tags=["skills"])

_SKILLS_DIR = Path(__file__).parent.parent / "skills"


# ── Pydantic models ───────────────────────────────────────────────────────────

class SkillFile(BaseModel):
    filename: str
    file_type: str
    content: str


class CatalogSkill(BaseModel):
    name: str
    description: str
    content: str           # SKILL.md body (without frontmatter)
    emoji: Optional[str] = None
    homepage: Optional[str] = None
    category: Optional[str] = None
    is_system: bool = True
    files: List[SkillFile] = []
    enabled: bool = False  # user-specific


# ── Filesystem helpers ────────────────────────────────────────────────────────

def _file_type(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    return {
        ".md": "markdown", ".py": "python", ".js": "javascript",
        ".ts": "typescript", ".json": "json", ".yaml": "yaml",
        ".yml": "yaml", ".sh": "bash", ".txt": "text", ".html": "html",
    }.get(ext, "text")


def _parse_skill_dir(skill_dir: Path) -> Optional[dict]:
    """Read a skill directory and return its metadata + file contents."""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return None

    raw = skill_md.read_text(encoding="utf-8")

    # Parse YAML frontmatter
    meta: dict = {}
    body = raw
    if raw.startswith("---"):
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", raw, re.DOTALL)
        if match:
            for line in match.group(1).splitlines():
                if ":" in line:
                    k, _, v = line.partition(":")
                    meta[k.strip()] = v.strip().strip('"').strip("'")
            body = match.group(2).strip()

    # Collect supporting files (everything except SKILL.md)
    files = []
    for path in sorted(skill_dir.rglob("*")):
        if not path.is_file():
            continue
        if "__pycache__" in path.parts or path.name.startswith("."):
            continue
        if path == skill_md:
            continue
        try:
            rel = str(path.relative_to(skill_dir))
            files.append(SkillFile(
                filename=rel,
                file_type=_file_type(path.name),
                content=path.read_text(encoding="utf-8"),
            ))
        except Exception:
            pass

    return {
        "name": meta.get("name") or skill_dir.name,
        "description": meta.get("description", ""),
        "content": body,
        "emoji": meta.get("emoji"),
        "homepage": meta.get("homepage"),
        "category": meta.get("category"),
        "is_system": True,
        "files": files,
    }


def _load_all_skills() -> dict[str, dict]:
    """Return a dict of skill_name → metadata for all skills on disk."""
    skills: dict[str, dict] = {}
    if not _SKILLS_DIR.exists():
        return skills
    for skill_dir in sorted(_SKILLS_DIR.iterdir()):
        if skill_dir.is_dir():
            data = _parse_skill_dir(skill_dir)
            if data:
                skills[data["name"]] = data
    return skills


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/catalog", response_model=List[CatalogSkill])
async def list_catalog(user_id: str):
    """All available skills merged with the user's enabled state."""
    all_skills = _load_all_skills()

    async with get_db_session() as db:
        user_skills = await skills_crud.get_user_skills(db, user_id)
    enabled_map = {us.skill_name: us.enabled for us in user_skills}

    return [
        CatalogSkill(
            **data,
            enabled=enabled_map.get(data["name"], data.get("is_system", False)),
        )
        for data in all_skills.values()
    ]


class ToggleRequest(BaseModel):
    enabled: bool


@router.post("/catalog/{skill_name}/toggle", response_model=CatalogSkill)
async def toggle_skill(skill_name: str, user_id: str, body: ToggleRequest):
    """Enable or disable a skill for a user."""
    all_skills = _load_all_skills()
    if skill_name not in all_skills:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")

    async with get_db_session() as db:
        await skills_crud.toggle_skill(db, user_id, skill_name, body.enabled)
        await db.commit()

    return CatalogSkill(**all_skills[skill_name], enabled=body.enabled)
