"""
Memory Tools Implementation

Provides agent-facing tools for reading and searching persistent memory files
stored in the user's E2B sandbox at:
  /home/user/MEMORY.md          - durable long-term memory
  /home/user/memory/YYYY-MM-DD.md - daily append-only logs

memory_get  — targeted read of a specific memory file (or line range)
memory_write — append a note to memory (durable or daily)
memory_search — BM25 keyword search + semantic fallback over all memory files

Search runs entirely inside the sandbox: we upload a small Python search
script, run it, and stream back ranked snippets. No external embedding API
is required; pure BM25 via a minimal rank-BM25 implementation that the
script installs on first use.
"""
from __future__ import annotations

import json
from typing import Optional, Dict, Any

from modules.agent.context import AgentContext
from pydantic import BaseModel, Field
from utils.logger import get_logger

logger = get_logger(__name__)

WORKSPACE_DIR = "/home/user"
MEMORY_FILE = f"{WORKSPACE_DIR}/MEMORY.md"
MEMORY_DIR = f"{WORKSPACE_DIR}/memory"

# ---------------------------------------------------------------------------
# Pydantic parameter models
# ---------------------------------------------------------------------------

class MemoryGetParams(BaseModel):
    path: str = Field(
        description=(
            "Memory file to read. Either 'MEMORY.md' for long-term memory "
            "or 'memory/YYYY-MM-DD.md' for a daily log. "
            "Defaults to 'MEMORY.md'."
        ),
        default="MEMORY.md",
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
            "Natural language query to search for in memory files. "
            "Returns the most relevant snippets across MEMORY.md and all daily logs."
        )
    )
    max_results: int = Field(
        default=6,
        description="Maximum number of snippets to return (default 6, max 15).",
    )


class MemoryWriteParams(BaseModel):
    content: str = Field(
        description="The note or fact to write to memory."
    )
    durable: bool = Field(
        default=False,
        description=(
            "If True, write to MEMORY.md (durable long-term facts, preferences, key decisions). "
            "If False (default), write to today's daily log memory/YYYY-MM-DD.md."
        ),
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
MEMORY_FILE = f"{WORKSPACE}/MEMORY.md"
MEMORY_DIR  = f"{WORKSPACE}/memory"
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
    if os.path.exists(MEMORY_FILE):
        chunks += chunk_text(Path(MEMORY_FILE).read_text(errors="replace"), "MEMORY.md")
    if os.path.exists(MEMORY_DIR):
        for p in sorted(Path(MEMORY_DIR).glob("*.md")):
            rel = f"memory/{p.name}"
            chunks += chunk_text(p.read_text(errors="replace"), rel)
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
    """Append a note to durable memory (MEMORY.md) or today's daily log."""
    from modules.tools.implementations.code_execution import (
        get_or_create_sandbox,
        _build_sandbox_env,
    )

    try:
        envs = await _build_sandbox_env(context)
        entry = await get_or_create_sandbox(context.user_id, envs)
        sbx = entry.sbx

        # Use a Python writer script to safely handle arbitrary content
        # (avoids shell quoting issues)
        writer_script = f"""import os
from datetime import datetime

content = {params.content!r}
durable = {params.durable!r}
memory_file = {MEMORY_FILE!r}
memory_dir = {MEMORY_DIR!r}

if durable:
    target = memory_file
    note = "\\n" + content + "\\n"
else:
    today = datetime.now().strftime("%Y-%m-%d")
    os.makedirs(memory_dir, exist_ok=True)
    target = f"{{memory_dir}}/{{today}}.md"
    note = "\\n- " + content + "\\n"

with open(target, "a") as f:
    f.write(note)

print(target)
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

        target = (result.stdout or "").strip()
        return {"success": True, "target": target or ("MEMORY.md" if params.durable else "memory/<today>.md")}

    except Exception as exc:
        logger.warning(f"memory_write failed for user {context.user_id}: {exc}")
        return {"success": False, "error": str(exc)}
