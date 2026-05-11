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
import json
import re

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


_HEREDOC_PATTERN = re.compile(
    r"cat\s+>>\s*(\S+)\s*<<\s*['\"]?(\w+)['\"]?\n(.*?)\n\2",
    re.DOTALL,
)
_HEREDOC_OVERWRITE_PATTERN = re.compile(
    r"cat\s+>\s*(\S+)\s*<<\s*['\"]?(\w+)['\"]?\n(.*?)\n\2",
    re.DOTALL,
)

_MIN_LINES_TO_SUMMARIZE = 15


def _summarize_file_writes(messages: List[Dict[str, Any]], protected_ids: Set[str]) -> Tuple[List[Dict[str, Any]], int]:
    """
    Replace heredoc file-writing bash tool call args with a short summary.
    The script is already on disk — no need to replay it in context.

    Only summarizes calls with >= _MIN_LINES_TO_SUMMARIZE lines of heredoc content.
    Protected (recent) tool calls are left untouched.

    Returns (new message list, count of summarized calls).
    """
    result = []
    summarized = 0

    for msg in messages:
        if msg.get("role") != "assistant" or not msg.get("tool_calls"):
            result.append(msg)
            continue

        new_tool_calls = []
        changed = False
        for tc in msg.get("tool_calls", []):
            tc_id = tc.get("id")
            fn = tc.get("function", {})
            if fn.get("name") != "bash" or tc_id in protected_ids:
                new_tool_calls.append(tc)
                continue

            args_str = fn.get("arguments", "")
            try:
                args = json.loads(args_str) if isinstance(args_str, str) else args_str
            except (json.JSONDecodeError, TypeError):
                new_tool_calls.append(tc)
                continue

            cmd = args.get("cmd", "") if isinstance(args, dict) else ""
            if not cmd:
                new_tool_calls.append(tc)
                continue

            new_cmd = cmd
            any_replaced = False
            for pattern in (_HEREDOC_OVERWRITE_PATTERN, _HEREDOC_PATTERN):
                def _replace_match(m):
                    nonlocal any_replaced
                    filepath = m.group(1)
                    body = m.group(3)
                    line_count = body.count("\n") + 1
                    if line_count < _MIN_LINES_TO_SUMMARIZE:
                        return m.group(0)
                    any_replaced = True
                    op = ">>" if pattern is _HEREDOC_PATTERN else ">"
                    return f"# [wrote {line_count} lines to {filepath}]\ncat {op} {filepath} << 'SUMMARIZED'\n# ... content on disk ...\nSUMMARIZED"

                new_cmd = pattern.sub(_replace_match, new_cmd)

            if any_replaced:
                new_args = dict(args) if isinstance(args, dict) else {"cmd": new_cmd}
                if isinstance(args, dict):
                    new_args["cmd"] = new_cmd
                new_tc = copy.deepcopy(tc)
                new_tc["function"]["arguments"] = json.dumps(new_args)
                new_tool_calls.append(new_tc)
                changed = True
                summarized += 1
            else:
                new_tool_calls.append(tc)

        if changed:
            msg_copy = copy.copy(msg)
            msg_copy["tool_calls"] = new_tool_calls
            result.append(msg_copy)
        else:
            result.append(msg)

    return result, summarized


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

    # --- Phase 0: Summarize file-writing bash calls ---
    # Scripts written via heredoc are already on disk. Replace the full
    # source in tool call args with a short summary to save context.
    messages, file_write_count = _summarize_file_writes(messages, protected_ids)

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

    if capped_count or evicted_count or file_write_count:
        logger.debug(
            f"Session pruner: summarized {file_write_count} file writes, "
            f"capped {capped_count}, evicted {evicted_count} tool results, "
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
