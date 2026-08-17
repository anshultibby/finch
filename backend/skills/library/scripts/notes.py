"""
Navigate a body of markdown notes the way a person navigates a filing cabinet.

The problem this solves: an agent that reads whole files doesn't scale. A file
it read once stays in the context window and is re-sent on every later step of
the run, so a long document is charged dozens of times over. The instinct to fix
that with rotation or truncation is wrong — it throws away material. People
don't truncate their notes; they *file* them and navigate by structure:

    index()      what documents exist            — the shelf
    outline()    what's in this document         — the table of contents
    read()       one section of one document     — the chapter you wanted
    find()       which document/section mentions X — the back-of-book index

Nothing here is a special format. These are plain markdown files with `#`
headings, readable by a human, greppable from bash, editable by hand. The
structure IS the access mechanism: write good headings and everything below
works. Write one 5,000-line file with no headings and nothing can help you.

Filing conventions live in the skill's SKILL.md — one document per subject,
dated entries in dated files, one file per task.

Two trees are addressable, split by who the audience is:

    stocks/, tasks/   shared with the user  -> synced to the Analysis and
                                               Tasks views in the app
    everything else   the agent's own wiki  -> store_files

The leading segment routes it, so `read()` and `write_chat_file()` agree on
where a path points. Anything the user should be able to see gets written
through `write_chat_file` so the sync hook fires.
"""
import os
import re
import time
from typing import Any, Dict, List, Optional

ROOT = os.environ.get("LIBRARY_ROOT", "/home/user/store")
# The shared tree. Written through write_chat_file so the sync hooks fire; this
# is the same directory on disk, for reading.
SHARED_ROOT = os.environ.get("LIBRARY_SHARED_ROOT", "/home/user/chat_files")
SHARED_PREFIXES = ("stocks", "tasks")

_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_FENCE = re.compile(r"^\s*(```|~~~)")


# ── structure ────────────────────────────────────────────────────────────────

def _headings(lines: List[str]) -> List[Dict[str, Any]]:
    """Headings with 1-indexed line numbers, ignoring anything inside a code
    fence (`# comment` in a python block is not a heading)."""
    out, in_fence = [], False
    for i, line in enumerate(lines, 1):
        if _FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = _HEADING.match(line)
        if m:
            out.append({"level": len(m.group(1)), "title": m.group(2), "line": i})
    return out


def _resolve(path: str) -> str:
    """Absolute paths are honoured. `stocks/` and `tasks/` route to the shared
    tree; everything else resolves under the agent's own store."""
    path = (path or "").strip()
    if path.startswith("/"):
        return path
    if path.split("/", 1)[0] in SHARED_PREFIXES:
        return os.path.join(SHARED_ROOT, path)
    return os.path.join(ROOT, path)


def _relative(path: str) -> str:
    """Invert _resolve, so what comes out of find()/index() can go back in."""
    for base in (SHARED_ROOT, ROOT):
        if path.startswith(base + os.sep):
            return os.path.relpath(path, base)
    return path


def _read_lines(path: str) -> List[str]:
    with open(_resolve(path), errors="replace") as f:
        return f.read().splitlines()


def _docs(root: Optional[str] = None) -> List[str]:
    """Markdown documents under `root`. An empty root means the whole library —
    both the store and the research tree."""
    bases = ([ROOT] + [os.path.join(SHARED_ROOT, p) for p in SHARED_PREFIXES]
             if not root else [_resolve(root)])
    found = []
    for base in bases:
        if os.path.isfile(base):
            found.append(base)
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
            for name in sorted(filenames):
                if name.endswith((".md", ".markdown")):
                    found.append(os.path.join(dirpath, name))
    return sorted(found)


def frontmatter(path: str) -> Dict[str, Any]:
    """YAML-ish frontmatter as a dict — the `status: open` / `review: 2026-08-20`
    block at the top of a task file. Deliberately tiny: scalars and inline
    `[a, b]` lists, which is all the conventions use. {} if there is none."""
    try:
        lines = _read_lines(path)
    except OSError:
        return {}
    if not lines or lines[0].strip() != "---":
        return {}
    meta: Dict[str, Any] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" not in line:
            continue
        key, _, raw = line.partition(":")
        val = raw.strip().split("  #")[0].strip()
        if val.startswith("[") and val.endswith("]"):
            meta[key.strip()] = [v.strip() for v in val[1:-1].split(",") if v.strip()]
        else:
            meta[key.strip()] = val
    return meta


# ── the shelf ────────────────────────────────────────────────────────────────

def index(root: str = "", depth: int = 2) -> List[Dict[str, Any]]:
    """The shelf: every document under `root` with its title, its sections, when
    it was last touched, and **what it would cost to read** — so you can budget
    before you fetch rather than discovering the size afterwards.

        index()                  -> the whole library, ~1 token per document
        index("tasks")           -> the task board, with status/review from
                                    each file's frontmatter
        index("stocks")          -> what companies you've written up

    Read this first. Then outline() the one document you want, then read() the
    one section of it you actually need. Newest first, because recency is the
    strongest relevance signal you have for free.
    """
    out = []
    for path in _docs(root):
        try:
            lines = _read_lines(path)
        except OSError:
            continue
        heads = _headings(lines)
        title = next((h["title"] for h in heads if h["level"] == 1), None)
        entry = {
            "path": _relative(path),
            "title": title or os.path.basename(path),
            "tokens": sum(len(line) for line in lines) // 4,
            "modified": time.strftime("%Y-%m-%d", time.localtime(os.path.getmtime(path))),
            "sections": [h["title"] for h in heads if 2 <= h["level"] <= depth],
        }
        entry.update(frontmatter(path))
        out.append(entry)
    return sorted(out, key=lambda e: e["modified"], reverse=True)


# ── the table of contents ────────────────────────────────────────────────────

def outline(path: str, max_depth: int = 6) -> List[Dict[str, Any]]:
    """The heading tree of one document, with line numbers. Skim this before
    reading — it's a few dozen tokens and tells you which section you want.

        outline("research/symbols/NVDA.md")
        -> [{"level": 2, "title": "Thesis", "line": 3}, ...]
    """
    return [h for h in _headings(_read_lines(path)) if h["level"] <= max_depth]


# ── the chapter ──────────────────────────────────────────────────────────────

def read(path: str, heading: Optional[str] = None,
         start_line: Optional[int] = None, end_line: Optional[int] = None) -> str:
    """Read a document, or — far better — one section of it.

        read("research/symbols/NVDA.md", "Thesis")   one section
        read("notes.md", start_line=40, end_line=80) an explicit range
        read("short.md")                             the whole thing

    `heading` matches case-insensitively on substring, and returns everything
    from that heading down to the next heading of the same or higher level —
    i.e. the section plus its subsections, which is what you meant.
    """
    lines = _read_lines(path)

    if heading:
        heads = _headings(lines)
        want = heading.strip().lower()
        match = next((h for h in heads if h["title"].strip().lower() == want), None) \
            or next((h for h in heads if want in h["title"].lower()), None)
        if not match:
            available = ", ".join(h["title"] for h in heads[:20]) or "none"
            raise KeyError(f"No heading matching {heading!r} in {path}. Headings: {available}")
        start = match["line"]
        end = next((h["line"] - 1 for h in heads
                    if h["line"] > match["line"] and h["level"] <= match["level"]), len(lines))
        return "\n".join(lines[start - 1:end]).rstrip()

    if start_line or end_line:
        return "\n".join(lines[(start_line or 1) - 1:(end_line or len(lines))]).rstrip()

    return "\n".join(lines)


# ── the back-of-book index ───────────────────────────────────────────────────

def find(query: str, root: str = "", limit: int = 20,
         context_chars: int = 160) -> List[Dict[str, Any]]:
    """Where is X discussed? Returns locations, not documents — each hit carries
    the document, the section it's under, the line, and a snippet.

        find("dilution")
        -> [{"path": "trading/journal/2026-06.md", "heading": "2026-06-12",
             "line": 88, "snippet": "...serial reverse splits..."}]

    Read the hit you care about with read(path, heading=...). This is how you
    reach old material without pulling any of it into context wholesale.
    """
    q = (query or "").lower()
    if not q:
        return []
    hits = []
    for path in _docs(root):
        try:
            lines = _read_lines(path)
        except OSError:
            continue
        heads = _headings(lines)
        for i, line in enumerate(lines, 1):
            if q not in line.lower():
                continue
            section = None
            for h in heads:
                if h["line"] <= i:
                    section = h["title"]
                else:
                    break
            col = line.lower().index(q)
            snippet = line[max(0, col - context_chars // 2):col + context_chars // 2].strip()
            hits.append({"path": _relative(path), "heading": section,
                         "line": i, "snippet": snippet})
            if len(hits) >= limit:
                return hits
    return hits


# ── writing ──────────────────────────────────────────────────────────────────

def _default_title(full_path: str) -> str:
    """H1 for a file being created. For `stocks/MU/thesis.md` the useful title
    is "MU — Thesis", not "Thesis" — the subject is the directory, and this H1
    becomes the note's title wherever it surfaces in the app."""
    rel = _relative(full_path)
    parts = rel.split(os.sep)
    stem = parts[-1][:-3] if parts[-1].endswith(".md") else parts[-1]
    pretty = stem.replace("-", " ").replace("_", " ").title()
    # 3+ segments means the parent directory is the subject (a ticker, a theme).
    if len(parts) >= 3:
        return f"{parts[-2]} — {pretty}"
    return pretty


def write_section(path: str, heading: str, body: str, level: int = 2,
                  mode: str = "replace") -> str:
    """Create or update ONE section, leaving the rest of the document alone.

        write_section("research/symbols/NVDA.md", "Thesis", "...")

    mode="replace" rewrites the section body; mode="append" adds to it. A
    heading that doesn't exist yet is appended as a new section, so this doubles
    as "start a section". Returns the resolved path.
    """
    full = _resolve(path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    lines = _read_lines(path) if os.path.exists(full) else []

    heads = _headings(lines)
    want = heading.strip().lower()
    match = next((h for h in heads if h["title"].strip().lower() == want), None)
    block = f"{'#' * level} {heading.strip()}\n\n{body.strip()}\n"

    if match is None:
        if not lines:
            lines = [f"# {_default_title(full)}", ""]
        new = lines + ([""] if lines and lines[-1].strip() else []) + block.splitlines()
    else:
        start = match["line"] - 1
        end = next((h["line"] - 1 for h in heads
                    if h["line"] > match["line"] and h["level"] <= match["level"]), len(lines))
        if mode == "append":
            existing = "\n".join(lines[start + 1:end]).strip()
            block = f"{'#' * match['level']} {match['title']}\n\n{existing}\n\n{body.strip()}\n"
        else:
            block = f"{'#' * match['level']} {match['title']}\n\n{body.strip()}\n"
        new = lines[:start] + block.splitlines() + lines[end:]

    with open(full, "w") as f:
        f.write("\n".join(new).rstrip() + "\n")
    return _relative(full)


def log(path: str, title: str, body: str) -> str:
    """Append a dated entry to a running document — the lab-notebook move.

        log("trading/journal/2026-08.md", "2026-08-17 nightly", "...")

    Entries are `##` sections, so outline() lists them and read(path, "2026-08-17
    nightly") pulls back exactly one. Keep the file per-month or per-quarter and
    a year of notes stays navigable without any archiving or rotation.
    """
    full = _resolve(path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    new_file = not os.path.exists(full)
    with open(full, "a") as f:
        if new_file:
            stem = os.path.basename(full)[:-3]
            f.write(f"# {stem}\n")
        f.write(f"\n## {title}\n\n{body.strip()}\n")
    return _relative(full)


def latest(path: str, n: int = 1) -> List[Dict[str, str]]:
    """The last `n` entries of a log document, newest last: [{title, body}].
    What a run needs to pick up where the last one left off."""
    if not os.path.exists(_resolve(path)):
        return []
    lines = _read_lines(path)
    entries = [h for h in _headings(lines) if h["level"] == 2]
    out = []
    for i, h in enumerate(entries):
        if n and i < len(entries) - n:
            continue
        end = entries[i + 1]["line"] - 1 if i + 1 < len(entries) else len(lines)
        out.append({"title": h["title"], "body": "\n".join(lines[h["line"]:end]).strip()})
    return out


# ── the task board ───────────────────────────────────────────────────────────

def tasks(status: str = "open", due_by: Optional[str] = None) -> List[Dict[str, Any]]:
    """The board: one row per task file, from `tasks/*.md` frontmatter.

        tasks()                        -> everything still open
        tasks(due_by="2026-08-18")     -> what's due for review today
        tasks(status=None)             -> everything, including done

    This is the work queue. A scheduled run should open with it rather than
    re-deriving its agenda from a diary — that's the whole point of one file
    per task: the index IS the queue.
    """
    rows = index("tasks")
    if status:
        rows = [r for r in rows if (r.get("status") or "open") == status]
    if due_by:
        rows = [r for r in rows if r.get("review") and str(r["review"]) <= due_by]
    return sorted(rows, key=lambda r: str(r.get("review") or "9999"))
