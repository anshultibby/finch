"""
Theses — why the user owns (or watches, or avoids) each stock, kept in Finch's
memory store so every proactive update can be judged against *their* story.

Storage follows the memory-store convention (store/ files the agent can read,
mirrored in store_files and editable in the Memory Store panel):

    store/theses/README.md   index — one line per thesis
    store/theses/NVDA.md     one file per symbol: frontmatter + sections + log

Source of truth is the store_files row. Every write goes through this module
(the app's /theses API, the agent's finch_api save_thesis/log_story, and
Memory Store edits of these files), which updates the row and — if the user's
sandbox is live — the file. A fresh sandbox connection re-seeds the files from
the rows, and store_sync skips this directory, so a stale sandbox copy can
never overwrite story-log entries the backend appended in the meantime.

The story check (`check_against_thesis`) asks one question of any development
that isn't routine noise: given what this user said would make them wrong, is
their thesis intact, weakened, or broken?
"""
import json
import re
from datetime import date
from typing import Dict, List, Optional

from utils.logger import get_logger

logger = get_logger(__name__)

THESES_DIR = "store/theses"
INDEX_FILE = f"{THESES_DIR}/README.md"
STANCES = ("own", "watch", "avoid")
STATUSES = ("intact", "weakened", "broken")
MAX_LOG = 25

_SYMBOL_RE = re.compile(r"^[A-Z0-9.\-^]{1,15}$")
_LOG_RE = re.compile(r"^- (\d{4}-\d{2}-\d{2}) · ([a-z_]+)(?: · ([a-z]+))? — (.*)$")


def normalize_symbol(symbol: str) -> str:
    sym = (symbol or "").strip().upper()
    if not _SYMBOL_RE.match(sym):
        raise ValueError(f"Invalid symbol: {symbol!r}")
    return sym


def path_for(symbol: str) -> str:
    return f"{THESES_DIR}/{normalize_symbol(symbol)}.md"


# ── markdown <-> dict ────────────────────────────────────────────────────────

def render_md(t: Dict) -> str:
    """One thesis as agent- and human-readable markdown."""
    lines = [
        "---",
        f"symbol: {t['symbol']}",
        f"stance: {t.get('stance') or 'own'}",
        f"written: {t.get('written') or date.today().isoformat()}",
        f"updated: {t.get('updated') or date.today().isoformat()}",
        "---",
        f"# {t['symbol']} — thesis",
        "",
        "## Why",
        (t.get("why") or "").strip() or "_(not written yet)_",
        "",
        "## What would make me wrong",
        (t.get("breaks") or "").strip() or "_(not written yet)_",
        "",
        "## Story log",
    ]
    for e in (t.get("log") or [])[-MAX_LOG:]:
        status = f" · {e['status']}" if e.get("status") else ""
        note = (e.get("note") or "").replace("\n", " ").strip()
        if e.get("source"):
            note += f" ({e['source']})"
        lines.append(f"- {e['date']} · {e.get('verdict') or 'news'}{status} — {note}")
    return "\n".join(lines) + "\n"


def parse_md(text: str, symbol: Optional[str] = None) -> Dict:
    """Inverse of render_md, tolerant of hand edits in the Memory Store panel."""
    meta: Dict[str, str] = {}
    body = text or ""
    m = re.match(r"^---\n(.*?)\n---\n?", body, re.S)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
        body = body[m.end():]

    sections: Dict[str, List[str]] = {}
    current = None
    for line in body.splitlines():
        if line.startswith("## "):
            current = line[3:].strip().lower()
            sections[current] = []
        elif current is not None:
            sections[current].append(line)

    def _section(*names: str) -> str:
        for n in names:
            if n in sections:
                text = "\n".join(sections[n]).strip()
                return "" if text == "_(not written yet)_" else text
        return ""

    log = []
    for line in sections.get("story log", []):
        lm = _LOG_RE.match(line.strip())
        if lm:
            log.append({"date": lm.group(1), "verdict": lm.group(2), "status": lm.group(3), "note": lm.group(4)})

    stance = meta.get("stance", "own")
    return {
        "symbol": (meta.get("symbol") or symbol or "").upper(),
        "stance": stance if stance in STANCES else "own",
        "written": meta.get("written"),
        "updated": meta.get("updated"),
        "why": _section("why", "why i own it"),
        "breaks": _section("what would make me wrong", "what would break it"),
        "log": log,
    }


def render_index(theses: List[Dict]) -> str:
    lines = [
        "# Theses",
        "",
        "Why the user owns, watches or avoids each stock — one file per symbol. Judge every "
        "move and news item on these names against the user's own thesis, and log what "
        "you find. Don't edit these files directly: use save_thesis() / log_story() from "
        "skills.finch_api.scripts so the app sees the change.",
        "",
    ]
    for t in sorted(theses, key=lambda x: x["symbol"]):
        gist = (t.get("why") or "").strip().splitlines()[0][:100] if t.get("why") else "(no thesis yet)"
        lines.append(f"- [{t['symbol']}]({t['symbol']}.md) — {t.get('stance', 'own')} · {gist}")
    return "\n".join(lines) + "\n"


# ── persistence (store_files row is the source of truth) ─────────────────────

async def _write_sandbox_if_live(user_id: str, files: Dict[str, Optional[str]]) -> None:
    """Mirror writes into a sandbox that's already running. Never wakes one up —
    a fresh connection re-seeds from the rows (seed_sandbox)."""
    try:
        from modules.tools.implementations.code_execution import _sandboxes
        entry = _sandboxes.get(user_id)
        if not entry:
            return
        await entry.sbx.commands.run(f"mkdir -p /home/user/{THESES_DIR}", timeout=5)
        for rel, content in files.items():
            if content is None:
                await entry.sbx.commands.run(f"rm -f /home/user/{rel}", timeout=5)
            else:
                await entry.sbx.files.write(f"/home/user/{rel}", content)
    except Exception as e:
        logger.debug(f"thesis sandbox mirror failed for {user_id} (non-fatal): {e}")


async def list_theses(user_id: str) -> List[Dict]:
    from sqlalchemy import select
    from core.database import get_db_session
    from models.store import StoreFile

    async with get_db_session() as db:
        rows = (await db.execute(
            select(StoreFile).where(
                StoreFile.user_id == user_id,
                StoreFile.filename.like(f"{THESES_DIR}/%.md"),
                StoreFile.filename != INDEX_FILE,
            )
        )).scalars().all()
    out = []
    for r in rows:
        sym = r.filename.rsplit("/", 1)[-1][:-3]
        t = parse_md(r.content or "", sym)
        t["symbol"] = sym  # the filename wins over a hand-edited frontmatter
        out.append(t)
    return sorted(out, key=lambda t: t["symbol"])


async def get_thesis(user_id: str, symbol: str) -> Optional[Dict]:
    from core.database import get_db_session
    from crud.store import get_store_file

    sym = normalize_symbol(symbol)
    async with get_db_session() as db:
        row = await get_store_file(db, user_id, path_for(sym))
    if not row or not row.content:
        return None
    t = parse_md(row.content, sym)
    t["symbol"] = sym
    return t


async def _persist(user_id: str, thesis: Dict) -> Dict:
    from core.database import get_db_session
    from crud.store import upsert_store_file

    content = render_md(thesis)
    async with get_db_session() as db:
        await upsert_store_file(db, user_id, path_for(thesis["symbol"]), content=content)
    index = render_index(await list_theses(user_id))
    async with get_db_session() as db:
        await upsert_store_file(db, user_id, INDEX_FILE, content=index)
    await _write_sandbox_if_live(user_id, {path_for(thesis["symbol"]): content, INDEX_FILE: index})
    return thesis


async def save_thesis(user_id: str, symbol: str, why: str, breaks: Optional[str] = None,
                      stance: str = "own") -> Dict:
    """Create or rewrite the user's thesis, keeping its story log."""
    sym = normalize_symbol(symbol)
    if stance not in STANCES:
        raise ValueError(f"stance must be one of {STANCES}")
    if not (why or "").strip():
        raise ValueError("why is required")
    existing = await get_thesis(user_id, sym) or {}
    today = date.today().isoformat()
    return await _persist(user_id, {
        "symbol": sym,
        "stance": stance,
        "why": why.strip(),
        "breaks": (breaks if breaks is not None else existing.get("breaks") or "").strip(),
        "written": existing.get("written") or today,
        "updated": today,
        "log": existing.get("log") or [],
    })


async def save_raw(user_id: str, symbol: str, content: str) -> Dict:
    """A Memory Store edit of a thesis file: re-render through the parser so the
    file stays well-formed and the index stays in sync."""
    sym = normalize_symbol(symbol)
    t = parse_md(content, sym)
    t["symbol"] = sym
    t["updated"] = date.today().isoformat()
    return await _persist(user_id, t)


async def log_story(user_id: str, symbol: str, note: str, verdict: str = "news",
                    status: Optional[str] = None, source: Optional[str] = None) -> Optional[Dict]:
    """Append a dated development to the thesis's story log. No-op without a thesis."""
    t = await get_thesis(user_id, symbol)
    if not t:
        return None
    entry = {
        "date": date.today().isoformat(),
        "verdict": verdict if verdict in ("noise", "news", "narrative_shift") else "news",
        "status": status if status in STATUSES else None,
        "note": (note or "").strip()[:400],
        "source": (source or "").strip()[:200] or None,
    }
    t["log"] = (t.get("log") or []) + [entry]
    t["log"] = t["log"][-MAX_LOG:]
    return await _persist(user_id, t)


async def delete_thesis(user_id: str, symbol: str) -> bool:
    from core.database import get_db_session
    from crud.store import delete_store_file, upsert_store_file

    path = path_for(symbol)
    async with get_db_session() as db:
        deleted = await delete_store_file(db, user_id, path)
    index = render_index(await list_theses(user_id))
    async with get_db_session() as db:
        await upsert_store_file(db, user_id, INDEX_FILE, content=index)
    await _write_sandbox_if_live(user_id, {path: None, INDEX_FILE: index})
    return deleted


async def seed_sandbox(user_id: str, sbx) -> None:
    """Write every thesis (and the index) from the rows into a freshly connected sandbox."""
    theses = await list_theses(user_id)
    if not theses:
        return
    await sbx.commands.run(f"mkdir -p /home/user/{THESES_DIR}", timeout=5)
    for t in theses:
        await sbx.files.write(f"/home/user/{path_for(t['symbol'])}", render_md(t))
    await sbx.files.write(f"/home/user/{INDEX_FILE}", render_index(theses))


# ── story check ──────────────────────────────────────────────────────────────

_CHECK_PROMPT = """You check a development against an investor's own thesis on a stock. You get their thesis (why they own/watch it, and what they said would make them wrong), their recent story log, and today's development with Finch's measured read of it.

Decide exactly one:
- "intact": the development doesn't touch the reasons they gave, or supports them.
- "weakened": it cuts against a reason they gave, or edges toward what they said would make them wrong, but doesn't settle it.
- "broken": what they said would make them wrong has happened, or a core reason is clearly gone.

Judge against THEIR stated reasons, not your own view of the stock. Routine price moves never weaken a thesis on their own. If their thesis is vague, say what's missing rather than guessing.

Respond with ONLY JSON: {"status": "intact" | "weakened" | "broken", "reason": "one or two plain sentences tying the development to their words"}"""


def _parse_check(text: str) -> Optional[Dict]:
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    if data.get("status") not in STATUSES or not data.get("reason"):
        return None
    return {"status": data["status"], "reason": str(data["reason"]).strip()}


async def check_against_thesis(user_id: str, thesis: Dict, development: str) -> Optional[Dict]:
    """{status, reason} for a development vs the user's thesis, or None on failure."""
    from services.monitoring.narrate import narrate

    log = "\n".join(
        f"- {e['date']} · {e.get('verdict')}{(' · ' + e['status']) if e.get('status') else ''} — {e.get('note')}"
        for e in (thesis.get("log") or [])[-5:]
    ) or "(empty)"
    content = (
        f"Stock: {thesis['symbol']} (stance: {thesis.get('stance', 'own')})\n"
        f"Their thesis — why: {thesis.get('why') or '(blank)'}\n"
        f"What they said would make them wrong: {thesis.get('breaks') or '(not stated)'}\n"
        f"Recent story log:\n{log}\n\n"
        f"Today's development:\n{development}\n\nReturn the JSON."
    )
    return await narrate(
        system_prompt=_CHECK_PROMPT,
        user_content=content,
        agent_type="thesis_check",
        max_tokens=600,
        user_id=user_id,
        parser=_parse_check,
    )


def describe_read(read: Dict) -> str:
    """A move_explainer result rendered as the 'development' text for a check."""
    parts = []
    if read.get("change_pct") is not None:
        parts.append(f"{read.get('symbol')} moved {read['change_pct']:+.2f}% today.")
    if read.get("verdict"):
        parts.append(f"Finch's read: {read['verdict']} ({read.get('driver') or 'unknown'} driver).")
    for k in ("headline", "explanation"):
        if read.get(k):
            parts.append(read[k])
    ctx = read.get("context") or {}
    if ctx.get("earnings"):
        parts.append(ctx["earnings"])
    return " ".join(parts)
