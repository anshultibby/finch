"""
Memory Tools Implementation (mostly dead code — agent uses bash directly)

Store layout in the user's E2B sandbox:

  /home/user/store/              — persistent memory wiki (user-visible)
    preferences.md, strategy.md, learnings.md
    journal/YYYY-MM-DD.md        — daily journal entries
    modules/*.py                 — reusable code

  (per-stock analysis lives separately: chat_files/stocks/{SYMBOL}/*.md,
   synced to the Analysis tab — see file_management._maybe_sync_stock_analysis)

  /home/user/workspace/          — ephemeral working memory
  /home/user/context/            — system-provided reference (chats, skills)
"""
from __future__ import annotations

import json
from typing import Optional, Dict, Any

from modules.agent.context import AgentContext
from pydantic import BaseModel, Field
from utils.logger import get_logger

logger = get_logger(__name__)

WORKSPACE_DIR = "/home/user"
STORE_DIR = f"{WORKSPACE_DIR}/store"
STORE_STRATEGY = f"{STORE_DIR}/strategy.md"
STORE_PREFERENCES = f"{STORE_DIR}/preferences.md"
STORE_LEARNINGS = f"{STORE_DIR}/learnings.md"
STORE_MODULES = f"{STORE_DIR}/modules"
STORE_JOURNAL = f"{STORE_DIR}/journal"
WORKING_DIR = f"{WORKSPACE_DIR}/workspace"
CONTEXT_DIR = f"{WORKSPACE_DIR}/context"
CHATS_DIR = f"{CONTEXT_DIR}/chats"

# ---------------------------------------------------------------------------
# Pydantic parameter models
# ---------------------------------------------------------------------------

class MemoryGetParams(BaseModel):
    path: str = Field(
        description=(
            "File to read from the store. Examples: "
            "'store/strategy.md', 'store/learnings.md', 'store/journal/2026-05-21.md', "
            "'store/modules/screener.py'. Defaults to 'store/learnings.md'."
        ),
        default="store/learnings.md",
    )
    start_line: Optional[int] = Field(
        None,
        description="First line to return (1-indexed). Omit to read from the start.",
    )
    end_line: Optional[int] = Field(
        None,
        description="Last line to return (inclusive). Omit to read to end of file.",
    )


class MemorySearchParams(BaseModel):
    query: str = Field(
        description=(
            "Natural language query to search across all store files "
            "(identity, strategy, preferences, learnings, journal entries, modules)."
        )
    )
    max_results: int = Field(
        default=6,
        description="Maximum number of snippets to return (default 6, max 15).",
    )


class MemoryWriteParams(BaseModel):
    content: str = Field(
        description="The content to write."
    )
    target: str = Field(
        default="journal",
        description=(
            "Where to write. One of: 'identity', 'strategy', 'preferences', "
            "'learnings', 'journal', or a modules/ path like 'modules/screener.py'."
        ),
    )
    mode: str = Field(
        default="append",
        description="'append' (default, for learnings/journal) or 'replace' (for identity/strategy/preferences/modules).",
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_memory_path(path: str) -> str:
    """Ensure path is absolute, rooted under WORKSPACE_DIR."""
    path = path.strip()
    if path.startswith("/"):
        return path
    return f"{WORKSPACE_DIR}/{path}"


def _resolve_write_target(target: str) -> str:
    """Resolve a write target name to an absolute sandbox path.

    Well-known shortcuts: identity, strategy, preferences, learnings, journal.
    Anything else is treated as a relative path under store/.
    The agent can create any file structure it wants.
    """
    target = target.strip()
    shortcuts = {
        "strategy": STORE_STRATEGY,
        "preferences": STORE_PREFERENCES,
        "learnings": STORE_LEARNINGS,
    }
    if target in shortcuts:
        return shortcuts[target]
    if target == "journal":
        return None  # resolved dynamically with today's date
    # Anything else is a relative path under store/
    return f"{STORE_DIR}/{target}"


def _target_to_store_filename(target: str, abs_path: str) -> str:
    """Convert an absolute sandbox path to a store-relative filename for the DB."""
    if abs_path.startswith(f"{WORKSPACE_DIR}/"):
        return abs_path[len(f"{WORKSPACE_DIR}/"):]
    return abs_path


# ---------------------------------------------------------------------------
# memory_get implementation
# ---------------------------------------------------------------------------

async def memory_get_impl(
    params: MemoryGetParams,
    context: AgentContext,
) -> Dict[str, Any]:
    """Read a memory file (or a line range within it) from the sandbox."""
    from modules.tools.implementations.code_execution import (
        get_or_create_sandbox,
        _build_sandbox_env,
    )

    try:
        envs = await _build_sandbox_env(context)
        entry = await get_or_create_sandbox(context.user_id, envs)
        sbx = entry.sbx

        abs_path = _resolve_memory_path(params.path)
        start_line = params.start_line or 1
        end_line = params.end_line or 0

        # Write a small reader script to avoid shell quoting issues
        reader_script = f"""import json, os
path = {abs_path!r}
if not os.path.exists(path):
    print(json.dumps({{"exists": False, "content": "", "total_lines": 0, "path": path}}))
else:
    with open(path) as f:
        lines = f.readlines()
    total = len(lines)
    s = max(0, {start_line} - 1)
    e = min({end_line} or total, total)
    print(json.dumps({{"exists": True, "content": "".join(lines[s:e]),
                        "total_lines": total, "start_line": s + 1, "end_line": e, "path": path}}))
"""
        reader_path = f"{WORKSPACE_DIR}/.finch_memory_get.py"
        await sbx.files.write(reader_path, reader_script)

        result = await sbx.commands.run(
            f"python3 {reader_path}",
            cwd=WORKSPACE_DIR,
            timeout=15,
            envs=entry.envs,
        )

        if result.exit_code != 0:
            cat_result = await sbx.commands.run(
                f"cat {abs_path} 2>/dev/null || echo ''",
                timeout=10,
                envs=entry.envs,
            )
            content = cat_result.stdout or ""
            return {"success": True, "path": params.path, "content": content, "exists": bool(content)}

        data = json.loads(result.stdout.strip())
        return {
            "success": True,
            "path": params.path,
            "content": data.get("content", ""),
            "exists": data.get("exists", False),
            "total_lines": data.get("total_lines", 0),
            "start_line": data.get("start_line"),
            "end_line": data.get("end_line"),
        }

    except Exception as exc:
        logger.warning(f"memory_get failed for user {context.user_id}: {exc}")
        return {"success": False, "error": str(exc), "content": ""}


# ---------------------------------------------------------------------------
# memory_search implementation
# ---------------------------------------------------------------------------

# The search script is uploaded to the sandbox and run there.
# It implements BM25 over chunked memory files — no server-side work needed.
_SEARCH_SCRIPT = r'''
import sys, os, json, re, math
from pathlib import Path
from collections import defaultdict

WORKSPACE = "/home/user"
STORE_DIR = f"{WORKSPACE}/store"
JOURNAL_DIR = f"{STORE_DIR}/journal"
MODULES_DIR = f"{STORE_DIR}/modules"
CHUNK_TOKENS = 400
OVERLAP      = 80

def tokenize(text):
    return re.findall(r"[a-z0-9']+", text.lower())

def chunk_text(text, source):
    words = text.split()
    chunks = []
    step = CHUNK_TOKENS - OVERLAP
    for i in range(0, max(1, len(words) - OVERLAP), step):
        snippet = " ".join(words[i : i + CHUNK_TOKENS])
        if snippet.strip():
            chunks.append({"text": snippet, "source": source, "word_offset": i})
    return chunks

def collect_chunks():
    chunks = []
    if not os.path.exists(STORE_DIR):
        return chunks
    # Walk entire store/ tree — agent can create any files it wants
    for root, dirs, files in os.walk(STORE_DIR):
        for fname in sorted(files):
            if not (fname.endswith(".md") or fname.endswith(".py") or fname.endswith(".txt")):
                continue
            p = Path(root) / fname
            rel = str(p).replace(WORKSPACE + "/", "")
            try:
                chunks += chunk_text(p.read_text(errors="replace"), rel)
            except Exception:
                pass
    return chunks

def bm25_score(query_tokens, chunk_tokens, idf, avgdl, k1=1.5, b=0.75):
    dl = len(chunk_tokens)
    freq = defaultdict(int)
    for t in chunk_tokens:
        freq[t] += 1
    score = 0.0
    for t in query_tokens:
        if t not in idf:
            continue
        tf = freq.get(t, 0)
        score += idf[t] * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * dl / avgdl))
    return score

query = sys.argv[1]
max_results = int(sys.argv[2]) if len(sys.argv) > 2 else 6

chunks = collect_chunks()
if not chunks:
    print(json.dumps([]))
    sys.exit(0)

tokenized = [tokenize(c["text"]) for c in chunks]
query_tokens = tokenize(query)

# Compute IDF
df = defaultdict(int)
N = len(tokenized)
for toks in tokenized:
    for t in set(toks):
        df[t] += 1
idf = {t: math.log((N - df[t] + 0.5) / (df[t] + 0.5) + 1) for t in df}

avgdl = sum(len(t) for t in tokenized) / N if N else 1

scored = []
for i, (chunk, toks) in enumerate(zip(chunks, tokenized)):
    s = bm25_score(query_tokens, toks, idf, avgdl)
    if s > 0:
        scored.append((s, i))

scored.sort(reverse=True)
top = scored[:max_results]

results = []
for score, idx in top:
    c = chunks[idx]
    results.append({
        "source": c["source"],
        "snippet": c["text"][:700],
        "score": round(score, 3),
    })

print(json.dumps(results))
'''


async def memory_search_impl(
    params: MemorySearchParams,
    context: AgentContext,
) -> Dict[str, Any]:
    """BM25 search over all memory files in the user's sandbox."""
    from modules.tools.implementations.code_execution import (
        get_or_create_sandbox,
        _build_sandbox_env,
    )

    try:
        envs = await _build_sandbox_env(context)
        entry = await get_or_create_sandbox(context.user_id, envs)
        sbx = entry.sbx

        search_path = f"{WORKSPACE_DIR}/.finch_memory_search.py"
        max_results = min(params.max_results, 15)

        # Upload the search script (idempotent — only if changed)
        await sbx.files.write(search_path, _SEARCH_SCRIPT)

        safe_query = params.query.replace("'", "'\\''")
        cmd = f"python3 {search_path} '{safe_query}' {max_results}"

        result = await sbx.commands.run(
            cmd,
            cwd=WORKSPACE_DIR,
            timeout=20,
            envs=entry.envs,
        )

        if result.exit_code != 0:
            logger.warning(f"memory_search script failed: {result.stderr}")
            return {
                "success": False,
                "error": f"Search failed: {result.stderr[:500]}",
                "results": [],
            }

        snippets = json.loads(result.stdout.strip() or "[]")
        return {
            "success": True,
            "query": params.query,
            "results": snippets,
            "count": len(snippets),
        }

    except Exception as exc:
        logger.warning(f"memory_search failed for user {context.user_id}: {exc}")
        return {"success": False, "error": str(exc), "results": []}


# ---------------------------------------------------------------------------
# memory_write implementation
# ---------------------------------------------------------------------------

async def memory_write_impl(
    params: MemoryWriteParams,
    context: AgentContext,
) -> Dict[str, Any]:
    """Write to a store target (journal, learnings, strategy, identity, preferences, or modules/)."""
    from modules.tools.implementations.code_execution import (
        get_or_create_sandbox,
        _build_sandbox_env,
    )

    try:
        envs = await _build_sandbox_env(context)
        entry = await get_or_create_sandbox(context.user_id, envs)
        sbx = entry.sbx

        target = params.target.strip()
        mode = params.mode.strip()
        abs_path = _resolve_write_target(target)

        writer_script = f"""import os
from datetime import datetime

content = {params.content!r}
target_name = {target!r}
mode = {mode!r}
store_dir = {STORE_DIR!r}
journal_dir = {STORE_JOURNAL!r}

# Ensure store directories exist
os.makedirs(store_dir, exist_ok=True)
os.makedirs(journal_dir, exist_ok=True)
os.makedirs(f"{{store_dir}}/modules", exist_ok=True)

if target_name == "journal":
    today = datetime.now().strftime("%Y-%m-%d")
    target_path = f"{{journal_dir}}/{{today}}.md"
    mode = "append"
elif {abs_path!r}:
    target_path = {abs_path!r}
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
else:
    target_path = f"{{store_dir}}/{{target_name}}"

if mode == "replace":
    with open(target_path, "w") as f:
        f.write(content)
else:
    note = "\\n- " + content + "\\n" if target_name in ("learnings", "journal") else "\\n" + content + "\\n"
    with open(target_path, "a") as f:
        f.write(note)

print(target_path)
"""
        writer_path = f"{WORKSPACE_DIR}/.finch_memory_write.py"
        await sbx.files.write(writer_path, writer_script)

        result = await sbx.commands.run(
            f"python3 {writer_path}",
            cwd=WORKSPACE_DIR,
            timeout=10,
            envs=entry.envs,
        )

        if result.exit_code != 0:
            return {"success": False, "error": (result.stderr or "")[:300]}

        written_path = (result.stdout or "").strip()

        # Sync to store_files DB
        if written_path:
            try:
                from core.database import get_db_session
                from crud.store import upsert_store_file

                full_content = await sbx.files.read(written_path, format="text")
                if full_content:
                    store_filename = _target_to_store_filename(target, written_path)
                    async with get_db_session() as db:
                        await upsert_store_file(
                            db, context.user_id, store_filename,
                            content=full_content, file_type="store",
                        )
                    logger.debug(f"Synced {store_filename} to store_files for user {context.user_id}")
            except Exception as e:
                logger.debug(f"Memory sync to store_files failed (non-fatal): {e}")

        return {"success": True, "target": written_path or target}

    except Exception as exc:
        logger.warning(f"memory_write failed for user {context.user_id}: {exc}")
        return {"success": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# strategy_write — thin wrapper for backward compat
# ---------------------------------------------------------------------------

class StrategyWriteParams(BaseModel):
    content: str = Field(
        description="The full strategy content to write. REPLACES the entire file."
    )


async def strategy_write_impl(
    params: StrategyWriteParams,
    context: AgentContext,
) -> Dict[str, Any]:
    """Write strategy.md — delegates to memory_write with target=strategy, mode=replace."""
    return await memory_write_impl(
        MemoryWriteParams(content=params.content, target="strategy", mode="replace"),
        context,
    )
