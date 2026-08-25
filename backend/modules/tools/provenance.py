"""
Tool-result provenance — source handles for citations.

A citation the agent writes (`[^N]`) must resolve to a real tool/API call that
ran this turn. We mint a short, model-visible handle (`src N`) for every
successful tool result, surface it in the text the model reads, and persist the
`N -> tool_call_id` mapping so a citation can be (a) enforced (unbacked numbers
are stripped before persist) and (b) opened to its raw payload in the UI.

The counter is per-chat and reset at the start of each turn (only one turn is
ever active per chat — enforced by context cancellation), so handle numbers in a
turn's final answer resolve against that turn's tool results.
"""
import re
from typing import Dict, List, Tuple

# chat_id -> highest source handle minted so far this turn.
_source_counters: Dict[str, int] = {}
# chat_id -> {source_ref: {"tool_call_id", "tool_name"}}. A shared, chat-scoped
# registry of every handle minted this turn. Sub-agents run under the SAME chat_id
# (delegate copies it), so their handles land here too — which is what lets the
# parent's enforcement pass resolve citations that came from delegated work,
# without threading anything back through delegate's return value.
_source_registry: Dict[str, Dict[int, Dict[str, str]]] = {}


def reset_source_refs(chat_id: str) -> None:
    """Start a fresh handle sequence + registry for a new turn."""
    _source_counters.pop(chat_id, None)
    _source_registry.pop(chat_id, None)


def next_source_ref(chat_id: str) -> int:
    """Mint the next monotonic source handle for this chat's current turn."""
    n = _source_counters.get(chat_id, 0) + 1
    _source_counters[chat_id] = n
    return n


def register_source(chat_id: str, source_ref: int, tool_call_id: str, tool_name: str) -> None:
    """Record a minted handle so citations to it can be verified this turn."""
    _source_registry.setdefault(chat_id, {})[source_ref] = {
        "tool_call_id": tool_call_id,
        "tool_name": tool_name,
    }


def registered_refs(chat_id: str) -> set:
    """All source handles minted this turn (parent agent + all sub-agents)."""
    return set(_source_registry.get(chat_id, {}).keys())


def tag_llm_content(source_ref: int, tool_name: str, content: str) -> str:
    """Prefix a tool result with the handle the model must cite it by.

    The model reads this block; the `[^N]` marker is what it copies into prose
    and into its Sources list. Keep the format stable — the prompt references it.
    """
    return f"«SOURCE [^{source_ref}]» (from {tool_name})\n{content}"


# --- Citation resolution / enforcement (used at message finalize) ---

# Inline citation markers the model emits: `[^3]` or `[^3](url)`.
_CITE_INLINE = re.compile(r"\[\^(\d+)\](?:\([^)]*\))?")
# Footnote definition lines: `[^3]: FMP income statement, Q2 FY27`.
_CITE_DEF = re.compile(r"^\[\^(\d+)\]:.*$", re.MULTILINE)


def cited_refs(content: str) -> List[int]:
    """All distinct source handles referenced inline in the answer."""
    return sorted({int(m.group(1)) for m in _CITE_INLINE.finditer(content)})


def enforce_citations(
    content: str, valid_refs: set,
) -> Tuple[str, List[int]]:
    """Strip citations that don't resolve to a real tool result this turn.

    A `[^N]` (and its `[^N]:` definition) whose N was never minted this turn is
    removed — the number it decorated stays, but the false provenance badge does
    not survive. Returns the cleaned content and the list of dropped handles so
    the caller can log/flag. Web-source citations that carry an inline URL are
    left alone even if unhandled, so external links keep working.
    """
    dropped: List[int] = []

    # 1. Remove whole `[^N]: …` definition lines whose N is unbacked, FIRST — before
    #    inline stripping mangles the `[^N]:` prefix and leaves an orphan `: …` line.
    def _strip_def(m: re.Match) -> str:
        n = int(m.group(1))
        if n in valid_refs or "http" in m.group(0):
            return m.group(0)
        return ""

    cleaned = _CITE_DEF.sub(_strip_def, content)

    # 2. Remove inline `[^N]` markers whose N is unbacked (the number they decorated
    #    stays; only the false provenance badge goes). External `[^N](http…)` links
    #    are left intact so real web citations keep working.
    def _strip_inline(m: re.Match) -> str:
        n = int(m.group(1))
        if m.group(0).endswith(")") and "http" in m.group(0):
            return m.group(0)
        if n in valid_refs:
            return m.group(0)
        dropped.append(n)
        return ""

    cleaned = _CITE_INLINE.sub(_strip_inline, cleaned)
    # Tidy any blank lines left where definition lines were removed.
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned, sorted(set(dropped))
