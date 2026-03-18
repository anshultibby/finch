"""
Session Pruner - evicts old tool results AND tool call arguments from the
in-memory message list before each LLM call to keep the context window
under budget.

This is transient: it only affects what is sent to the model for that request.
It never modifies the database or the ChatHistory object.

Strategy (adapted from OpenClaw's layered approach):
1. Cap any single tool result to CONTEXT_SINGLE_TOOL_RESULT_RATIO of the context window.
2. Protect the last KEEP_LAST_ASSISTANTS assistant messages and their tool results.
3. If total estimated tokens exceed CONTEXT_BUDGET_RATIO of the context window,
   evict old tool results oldest-first (replace with a placeholder) until under budget.
   When a tool result is evicted, the matching tool call arguments in the assistant
   message are also cleared to reclaim that space.
4. If still over CONTEXT_OVERFLOW_RATIO after eviction, signal that early compaction
   is needed.

No soft-trimming (head+tail) — tool results are either kept in full or evicted entirely.
"""
from typing import List, Dict, Any, Tuple, Set
import copy

from core.config import Config
from utils.logger import get_logger

logger = get_logger(__name__)

_EVICTED_PLACEHOLDER = "[tool output removed to free context]"
_CLEARED_ARGS = "{}"


def _estimate_tokens(messages: List[Dict[str, Any]]) -> int:
    total_chars = 0
    for msg in messages:
        content = msg.get("content") or ""
        if isinstance(content, str):
            total_chars += len(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    total_chars += len(block.get("text", ""))
        for tc in msg.get("tool_calls") or []:
            args = tc.get("function", {}).get("arguments", "")
            total_chars += len(args) if isinstance(args, str) else 0
    return total_chars // 4


def _content_chars(content) -> int:
    if not content:
        return 0
    if isinstance(content, str):
        return len(content)
    if isinstance(content, list):
        return sum(len(b.get("text", "")) for b in content if isinstance(b, dict))
    return 0


def _find_protected_tool_call_ids(messages: List[Dict[str, Any]], keep_last: int) -> set:
    """
    Return tool_call_ids belonging to the last `keep_last` assistant messages
    that have tool calls. Results for these IDs are protected from eviction.
    """
    assistant_indices = [
        i for i, m in enumerate(messages)
        if m.get("role") == "assistant" and m.get("tool_calls")
    ]
    protected_indices = set(assistant_indices[-keep_last:]) if assistant_indices else set()

    protected_ids: set = set()
    for idx in protected_indices:
        for tc in messages[idx].get("tool_calls") or []:
            tc_id = tc.get("id")
            if tc_id:
                protected_ids.add(tc_id)
    return protected_ids


def _clear_tool_call_args(messages: List[Dict[str, Any]], evicted_ids: Set[str]) -> None:
    """
    Clear the arguments of tool calls whose results were evicted.

    Mutates messages in place — caller must ensure they are copies.
    The tool call structure is preserved (name + id) so the API sequence
    stays valid, but the arguments are replaced with '{}' to free tokens.
    """
    if not evicted_ids:
        return

    for msg in messages:
        if msg.get("role") != "assistant" or not msg.get("tool_calls"):
            continue
        for tc in msg["tool_calls"]:
            if tc.get("id") in evicted_ids:
                tc["function"] = {
                    "name": tc["function"]["name"],
                    "arguments": _CLEARED_ARGS,
                }


def prune_messages(messages: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], bool]:
    """
    Return a pruned copy of `messages` suitable for sending to the LLM,
    plus a boolean indicating whether early compaction should be triggered.

    The original list is not modified.
    """
    if not Config.CONTEXT_PRUNE_ENABLED:
        return messages, False

    ctx_window = Config.CONTEXT_WINDOW_TOKENS
    keep_last = Config.CONTEXT_PRUNE_KEEP_LAST_ASSISTANTS
    single_cap_chars = int(ctx_window * Config.CONTEXT_SINGLE_TOOL_RESULT_RATIO * 4)
    budget_tokens = int(ctx_window * Config.CONTEXT_BUDGET_RATIO)
    overflow_tokens = int(ctx_window * Config.CONTEXT_OVERFLOW_RATIO)

    protected_ids = _find_protected_tool_call_ids(messages, keep_last)
    evicted_ids: Set[str] = set()

    # --- Phase 1: Cap oversized individual tool results ---
    phase1: List[Dict[str, Any]] = []
    capped_count = 0
    for msg in messages:
        if msg.get("role") == "tool":
            chars = _content_chars(msg.get("content"))
            tc_id = msg.get("tool_call_id")
            if chars > single_cap_chars and tc_id not in protected_ids:
                msg_copy = copy.copy(msg)
                msg_copy["content"] = _EVICTED_PLACEHOLDER
                phase1.append(msg_copy)
                capped_count += 1
                if tc_id:
                    evicted_ids.add(tc_id)
                continue
        phase1.append(msg)

    # --- Phase 2: Oldest-first eviction if over budget ---
    estimated = _estimate_tokens(phase1)
    evicted_count = 0

    if estimated > budget_tokens:
        # Collect indices of evictable tool results (oldest first, unprotected)
        evictable: List[int] = []
        for i, msg in enumerate(phase1):
            if (
                msg.get("role") == "tool"
                and msg.get("tool_call_id") not in protected_ids
                and msg.get("content") != _EVICTED_PLACEHOLDER
            ):
                evictable.append(i)

        # Evict oldest first until under budget
        phase1 = list(phase1)  # ensure we can mutate
        for idx in evictable:
            if _estimate_tokens(phase1) <= budget_tokens:
                break
            tc_id = phase1[idx].get("tool_call_id")
            phase1[idx] = copy.copy(phase1[idx])
            phase1[idx]["content"] = _EVICTED_PLACEHOLDER
            evicted_count += 1
            if tc_id:
                evicted_ids.add(tc_id)

        estimated = _estimate_tokens(phase1)

    # --- Phase 2b: Clear tool call arguments for evicted results ---
    if evicted_ids:
        # Deep-copy assistant messages that have evicted tool calls so we
        # don't mutate the originals, then clear their arguments.
        for i, msg in enumerate(phase1):
            if msg.get("role") != "assistant" or not msg.get("tool_calls"):
                continue
            has_evicted = any(tc.get("id") in evicted_ids for tc in msg["tool_calls"])
            if has_evicted:
                phase1[i] = copy.deepcopy(msg)
        _clear_tool_call_args(phase1, evicted_ids)

    if capped_count or evicted_count:
        logger.debug(
            f"Session pruner: capped {capped_count}, evicted {evicted_count} tool results, "
            f"cleared {len(evicted_ids)} tool call args "
            f"(est. tokens after: {estimated:,}, budget: {budget_tokens:,})"
        )

    # --- Phase 3: Check overflow → signal early compaction ---
    # Re-estimate after clearing args
    estimated = _estimate_tokens(phase1)
    needs_compaction = estimated > overflow_tokens

    if needs_compaction:
        logger.warning(
            f"Session pruner: still over overflow threshold after eviction "
            f"({estimated:,} > {overflow_tokens:,}) — requesting early compaction"
        )

    return phase1, needs_compaction
