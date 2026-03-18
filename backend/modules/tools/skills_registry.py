"""
Skills registry — reads skill metadata from backend/skills/*/SKILL.md.

Provides:
- get_skills_description()  for LLM context
- SKILL_ENV_KEYS            mapping of env var → (service_name, owner)
                            owner: "system" (developer-provided) | "user" (per-user)
"""
from pathlib import Path
from typing import Dict, Tuple

_SKILLS_DIR = Path(__file__).parent.parent.parent / "skills"


# ---------------------------------------------------------------------------
# Ownership registry
# Which env vars are system-level (from .env / global config) vs user-level
# (stored per-user in the DB and set via Settings > API Keys).
# ---------------------------------------------------------------------------

# env_var -> (service_name_for_ApiKeyService, owner)
SKILL_ENV_KEYS: Dict[str, Tuple[str, str]] = {
    # System keys — developer provides, shared across all users
    "FMP_API_KEY":            ("FMP",      "system"),
    "POLYGON_API_KEY":        ("POLYGON",  "system"),
    "SERPER_API_KEY":         ("SERPER",   "system"),
    "ODDS_API_KEY":           ("ODDS",     "system"),
    "REDDIT_CLIENT_ID":       ("REDDIT",   "system"),
    "REDDIT_CLIENT_SECRET":   ("REDDIT",   "system"),
    "SNAPTRADE_CLIENT_ID":    ("SNAPTRADE","system"),
    "SNAPTRADE_CONSUMER_KEY": ("SNAPTRADE","system"),

    # User keys — each user provides their own via Settings > API Keys
    "KALSHI_API_KEY_ID":  ("KALSHI", "user"),
    "KALSHI_PRIVATE_KEY": ("KALSHI", "user"),
}


# ---------------------------------------------------------------------------
# SKILL.md parsing
# ---------------------------------------------------------------------------

def _parse_frontmatter(skill_md: Path) -> dict:
    """Parse YAML-ish frontmatter from a SKILL.md file."""
    try:
        text = skill_md.read_text(encoding="utf-8")
        if not text.startswith("---"):
            return {}
        end = text.find("\n---", 3)
        if end == -1:
            return {}
        result: dict = {}
        current_list_key = None
        for line in text[3:end].splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.startswith("- ") and current_list_key:
                result.setdefault(current_list_key, []).append(stripped[2:].strip())
            elif ":" in stripped:
                key, _, value = stripped.partition(":")
                value = value.strip().strip('"').strip("'")
                if value == "[]":
                    result[key.strip()] = []
                    current_list_key = None
                elif value:
                    result[key.strip()] = value
                    current_list_key = None
                else:
                    current_list_key = key.strip()
        return result
    except Exception:
        return {}


def get_skill_env_keys(skill_name: str) -> list[str]:
    """Return the list of required env vars declared in a skill's SKILL.md."""
    skill_md = _SKILLS_DIR / skill_name / "SKILL.md"
    if not skill_md.exists():
        return []
    meta = _parse_frontmatter(skill_md)
    return meta.get("env", [])


def get_all_skill_packages() -> list[str]:
    """
    Return a deduplicated list of all pip packages required by all skills.
    Reads `requires.bins` from each skill's SKILL.md frontmatter.
    Used to pre-install packages when the sandbox is first created.
    """
    if not _SKILLS_DIR.exists():
        return []
    packages: list[str] = []
    seen: set[str] = set()
    for skill_dir in sorted(_SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir() or skill_dir.name.startswith("_"):
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        meta = _parse_frontmatter(skill_md)
        for pkg in meta.get("bins", []):
            if pkg and pkg not in seen:
                packages.append(pkg)
                seen.add(pkg)
    return packages


# ---------------------------------------------------------------------------
# LLM context description
# ---------------------------------------------------------------------------

def get_skills_description() -> str:
    """Build a skills description string for LLM context."""
    if not _SKILLS_DIR.exists():
        return _static_skills_description()

    skills = []
    for skill_dir in sorted(_SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        meta = _parse_frontmatter(skill_md)
        name = meta.get("name") or skill_dir.name
        description = meta.get("description", "")
        category = (meta.get("category") or "general").replace("_", " ").title()
        skills.append((category, name, description))

    if not skills:
        return _static_skills_description()

    lines = []
    current_category = None
    for category, name, description in sorted(skills):
        if category != current_category:
            lines.append(f"\n**{category}:**")
            current_category = category
        lines.append(f"- `{name}` — {description}")

    return f"""
**AVAILABLE SYSTEM SKILLS**

System skills give you ready-made Python APIs for external data sources.
Each skill's files are at `/home/user/skills/<name>/` in the sandbox.

{"".join(lines)}

**How to use a skill:**
1. Read its docs: `bash('cat /home/user/skills/<skill_name>/SKILL.md')`
2. Browse files: `bash('ls /home/user/skills/<skill_name>/scripts/')`
3. Import and use directly in your Python code:
```python
from skills.<skill_name>.scripts.<module> import <function>
```

**Load skills on demand** — only read the docs you actually need.
"""


def _static_skills_description() -> str:
    return """
**AVAILABLE SYSTEM SKILLS**

Skills are at `/home/user/skills/<name>/` in the sandbox.
Read any skill's docs on demand: `bash('cat /home/user/skills/<skill_name>/SKILL.md')`

Skills include: `polygon_io`, `financial_modeling_prep`, `tradingview`,
`kalshi_trading`, `snaptrade`, `reddit`
"""


# Keep old name working
generate_skills_description = get_skills_description
