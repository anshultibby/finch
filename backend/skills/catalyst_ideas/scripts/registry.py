"""
Scanner registry — how you write your own scanners and keep them.

A scanner is just a Python file that defines `scan() -> list[candidate]`. You
write it, save it here, and it survives across runs like the journal does. That
means you are not limited to the starter scanners: when you notice a catalyst
pattern nobody coded for — index-inclusion announcements, unusual insider
clusters, 13F changes, short-squeeze setups, sympathy moves off a peer's news —
write the scanner, save it, and it runs from then on.

    from skills.catalyst_ideas.scripts import registry

    registry.save("index_inclusion", '''
    from skills.catalyst_ideas.scripts import feeds, screen

    def scan():
        out = []
        for r in feeds.press_releases(300):
            if screen.is_litigation_spam(r["title"]):
                continue
            if "S&P 500" in r["title"] and "add" in r["title"].lower():
                out.append(screen.candidate(
                    r["symbol"], "index_inclusion", r["title"],
                    r["publishedDate"][:10], source_url=r.get("url")))
        return screen.screen(out)
    ''')

    registry.run("index_inclusion")      # -> candidates
    registry.run_all()                   # -> {name: candidates}

Rules for a scanner you write:
  - define `scan()` taking no required arguments, returning candidates
  - build them with screen.candidate() so the shape is right
  - end with screen.screen() so untradeable names are gone
  - keep it cheap: these run on a schedule, several per day

Scanners live in the persistent store, so review and prune them. One that stops
earning alpha (check list_ideas()'s by_catalyst breakdown) should be deleted,
not left running.
"""
from __future__ import annotations

import os
import re
import traceback
from typing import Any, Callable, Dict, List, Optional

SCANNER_DIR = os.environ.get(
    "CATALYST_SCANNER_DIR", "/home/user/store/catalyst_ideas/scanners"
)

_NAME_RE = re.compile(r"^[a-z0-9_]{2,40}$")


def _path(name: str) -> str:
    if not _NAME_RE.match(name):
        raise ValueError("scanner name must be lowercase letters, digits and underscores")
    return os.path.join(SCANNER_DIR, f"{name}.py")


def _ensure_dir() -> None:
    os.makedirs(SCANNER_DIR, exist_ok=True)


def save(name: str, source: str) -> str:
    """Write (or overwrite) a scanner. Compiles it first — a scanner that
    doesn't parse is never saved."""
    compile(source, f"<scanner:{name}>", "exec")  # raises SyntaxError early
    if "def scan(" not in source:
        raise ValueError("a scanner must define scan()")
    _ensure_dir()
    path = _path(name)
    with open(path, "w") as f:
        f.write(source)
    return path


def read(name: str) -> str:
    """The scanner's source — read it before editing so you don't clobber it."""
    with open(_path(name)) as f:
        return f.read()


def list_scanners() -> List[str]:
    if not os.path.isdir(SCANNER_DIR):
        return []
    return sorted(f[:-3] for f in os.listdir(SCANNER_DIR) if f.endswith(".py"))


def delete(name: str) -> bool:
    try:
        os.remove(_path(name))
        return True
    except FileNotFoundError:
        return False


def _load(name: str) -> Callable[[], List[Dict[str, Any]]]:
    src = read(name)
    ns: Dict[str, Any] = {"__name__": f"scanner_{name}"}
    exec(compile(src, f"<scanner:{name}>", "exec"), ns)
    fn = ns.get("scan")
    if not callable(fn):
        raise ValueError(f"scanner '{name}' defines no scan()")
    return fn


def run(name: str) -> List[Dict[str, Any]]:
    """Run one scanner. Exceptions propagate — you want to see them while
    developing a scanner."""
    return _load(name)() or []


def run_all(include: Optional[List[str]] = None) -> Dict[str, Any]:
    """Run every saved scanner. One broken scanner must not kill the sweep, so
    failures are captured per-scanner and returned under `_errors` for you to
    fix rather than raised."""
    names = include if include is not None else list_scanners()
    out: Dict[str, Any] = {}
    errors: Dict[str, str] = {}
    for n in names:
        try:
            out[n] = run(n)
        except Exception:
            errors[n] = traceback.format_exc(limit=3)
    if errors:
        out["_errors"] = errors
    return out
