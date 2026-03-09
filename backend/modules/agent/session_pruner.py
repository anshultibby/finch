"""
Session Pruner - trims old tool results from the in-memory message list
before each LLM call to keep the context window lean.

This is transient: it only affects what is sent to the model for that request.
It never modifies the database or the ChatHistory object.

Strategy (mirrors OpenClaw's approach):
- Protect the last KEEP_LAST_ASSISTANTS assistant messages and their tool results.
- For older tool results, soft-trim large ones (keep head + tail with an ellipsis)
  or hard-clear very large ones (replace with a placeholder).
- User messages and assistant text are never modified.
"""
from typing import List, Dict, Any
import copy

from core.config import Config
from utils.logger import get_logger

logger = get_logger(__name__)

_HARD_CLEAR_PLACEHOLDER = "[Old tool result cleared to save context]"
_SOFT_TRIM_HEAD = 1500
_SOFT_TRIM_TAIL = 1500


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
        # Count tool call arguments too
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


def _soft_trim(content: str, max_chars: int) -> str:
    if len(content) <= max_chars:
        return content
    head = content[:_SOFT_TRIM_HEAD]
    tail = content[-_SOFT_TRIM_TAIL:]
    omitted = len(content) - _SOFT_TRIM_HEAD - _SOFT_TRIM_TAIL
    return f"{head}\n... [{omitted:,} chars omitted] ...\n{tail}"


def _find_protected_tool_call_ids(messages: List[Dict[str, Any]], keep_last: int) -> set:
    """
    Return tool_call_ids belonging to the last `keep_last` assistant messages
    that have tool calls. Results for these IDs are protected from pruning.
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


def prune_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Return a pruned copy of `messages` suitable for sending to the LLM.

    The original list is not modified.
    """
    if not Config.CONTEXT_PRUNE_ENABLED:
        return messages

    estimated = _estimate_tokens(messages)
    # Only prune if we're using a meaningful amount of context
    # Threshold: 50k tokens (~200k chars) before we start trimming
    if estimated < 50000:
        return messages

    soft_max = Config.CONTEXT_SOFT_TRIM_MAX_CHARS
    hard_threshold = int(soft_max * 10 * Config.CONTEXT_HARD_CLEAR_RATIO)
    keep_last = Config.CONTEXT_PRUNE_KEEP_LAST_ASSISTANTS

    protected_ids = _find_protected_tool_call_ids(messages, keep_last)

    pruned = []
    trimmed_count = 0
    cleared_count = 0

    for msg in messages:
        if msg.get("role") != "tool":
            pruned.append(msg)
            continue

        tool_call_id = msg.get("tool_call_id")
        if tool_call_id in protected_ids:
            pruned.append(msg)
            continue

        content = msg.get("content") or ""
        chars = _content_chars(content)

        if chars <= soft_max:
            pruned.append(msg)
            continue

        msg_copy = copy.copy(msg)
        if chars > hard_threshold:
            msg_copy["content"] = _HARD_CLEAR_PLACEHOLDER
            cleared_count += 1
        else:
            if isinstance(content, str):
                msg_copy["content"] = _soft_trim(content, soft_max)
            trimmed_count += 1

        pruned.append(msg_copy)

    if trimmed_count or cleared_count:
        logger.debug(
            f"Session pruner: soft-trimmed {trimmed_count}, hard-cleared {cleared_count} tool results "
            f"(est. tokens before: {estimated:,})"
        )

    return pruned
