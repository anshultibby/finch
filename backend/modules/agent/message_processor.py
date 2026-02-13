"""
Message history processing and validation utilities
"""
from typing import List, Dict, Any, Set, Iterable
from datetime import datetime
import json

from utils.logger import get_logger

logger = get_logger(__name__)


def validate_and_fix_tool_calls(tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Validate tool call arguments JSON and fix malformed ones.
    
    This handles the case where the LLM streams incomplete/truncated JSON arguments.
    If we don't fix these, litellm will fail when trying to send them back to Anthropic.
    
    Args:
        tool_calls: List of tool calls from LLM response
        
    Returns:
        List of tool calls with valid JSON arguments (malformed ones get empty {})
    """
    if not tool_calls:
        return tool_calls
    
    fixed_calls = []
    for tc in tool_calls:
        tc_copy = tc.copy()
        if "function" in tc_copy:
            func = tc_copy["function"].copy()
            args_str = func.get("arguments", "")
            
            # Try to parse the JSON arguments
            if args_str:
                try:
                    json.loads(args_str)
                    # Valid JSON, keep as-is
                except json.JSONDecodeError as e:
                    # Malformed JSON indicates context overflow or output token limit
                    tool_name = func.get('name', 'unknown')
                    args_len = len(args_str)
                    
                    logger.error(
                        f"🚨 MALFORMED TOOL CALL - LLM output truncated!\n"
                        f"   Tool: {tool_name}\n"
                        f"   Args length: {args_len} chars\n"
                        f"   JSON error: {e}\n"
                        f"   Full raw args:\n"
                        f"   ----START----\n"
                        f"{args_str}\n"
                        f"   ----END----\n"
                        f"   → This usually means:\n"
                        f"     1. Context limit exceeded (too much history)\n"
                        f"     2. Output token limit hit (max_tokens too low for large file writes)\n"
                        f"     3. LLM stopped mid-generation\n"
                        f"   → Replacing with empty {{}} - tool will fail with missing args"
                    )
                    func["arguments"] = "{}"
            
            tc_copy["function"] = func
        fixed_calls.append(tc_copy)
    
    return fixed_calls


def _extract_tool_use_ids_from_content(content: Any) -> Set[str]:
    """
    Extract tool_use ids from Claude-style content blocks.
    
    content can be a list of blocks, or a JSON string encoding that list.
    """
    tool_use_ids: Set[str] = set()
    content_blocks: Iterable[Dict[str, Any]] = []
    
    if isinstance(content, list):
        content_blocks = content
    elif isinstance(content, str) and content.strip().startswith("["):
        try:
            parsed = json.loads(content)
            if isinstance(parsed, list):
                content_blocks = parsed
        except json.JSONDecodeError:
            return tool_use_ids
    
    for block in content_blocks:
        if isinstance(block, dict) and block.get("type") == "tool_use":
            tool_use_id = block.get("id") or block.get("tool_use_id")
            if tool_use_id:
                tool_use_ids.add(tool_use_id)
    
    return tool_use_ids


def _strip_tool_use_blocks(content: Any) -> Any:
    """
    Remove tool_use blocks from Claude-style content.
    
    Returns content with tool_use blocks removed; preserves text and other blocks.
    """
    if isinstance(content, list):
        return [block for block in content if not (isinstance(block, dict) and block.get("type") == "tool_use")]
    if isinstance(content, str) and content.strip().startswith("["):
        try:
            parsed = json.loads(content)
            if isinstance(parsed, list):
                cleaned = [block for block in parsed if not (isinstance(block, dict) and block.get("type") == "tool_use")]
                return json.dumps(cleaned)
        except json.JSONDecodeError:
            return content
    return content


def clean_incomplete_tool_calls(
    messages: List[Dict[str, Any]],
    pending_tool_calls: Set[str]
) -> List[Dict[str, Any]]:
    """
    Remove incomplete tool call sequences from message history
    
    Args:
        messages: List of API messages (includes system message at index 0)
        pending_tool_calls: Set of tool call IDs that don't have responses
        
    Returns:
        Cleaned message list with incomplete sequences removed
    """
    if not pending_tool_calls:
        return messages
    
    print(f"⚠️ Found incomplete tool call sequence with IDs: {pending_tool_calls}", flush=True)
    print(f"⚠️ Cleaning up chat history to remove incomplete tool calls", flush=True)
    
    # Keep system message and clean the rest
    cleaned_messages = [messages[0]]
    
    for msg in messages[1:]:
        # If this is an assistant message with tool calls, stop here
        if msg.get("role") == "assistant" and msg.get("tool_calls"):
            print(f"⚠️ Removing assistant message with tool_calls", flush=True)
            break
        
        # If this is an orphaned tool response, stop here
        if msg.get("role") == "tool":
            print(f"⚠️ Removing orphaned tool response: {msg.get('tool_call_id')}", flush=True)
            break
        
        cleaned_messages.append(msg)
    
    print(f"✅ Cleaned message history, now has {len(cleaned_messages)} messages", flush=True)
    return cleaned_messages


def enforce_tool_call_sequence(
    messages: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Ensure assistant tool_calls are immediately followed by tool results.
    
    Anthropic requires that any tool_use blocks are followed immediately by
    tool_result blocks in the next message(s). If this is not true, the API
    rejects the request. This function removes incomplete or out-of-order
    tool call sequences to keep the history valid.
    
    Args:
        messages: List of API messages (includes system message at index 0)
        
    Returns:
        Cleaned message list with only valid tool call sequences
    """
    if not messages:
        return messages
    
    cleaned: List[Dict[str, Any]] = []
    idx = 0
    
    # Preserve system message if present
    if messages[0].get("role") == "system":
        cleaned.append(messages[0])
        idx = 1
    
    while idx < len(messages):
        msg = messages[idx]
        role = msg.get("role")
        
        # Drop orphaned tool messages (no preceding assistant tool_calls)
        if role == "tool":
            logger.warning(
                "Dropping orphaned tool result without preceding tool_calls "
                f"(tool_call_id={msg.get('tool_call_id')})"
            )
            idx += 1
            continue
        
        # Validate assistant tool call sequences
        if role == "assistant" and (msg.get("tool_calls") or msg.get("content")):
            tool_calls = msg.get("tool_calls") or []
            tool_ids = [tc.get("id") for tc in tool_calls if tc.get("id")]
            tool_use_ids = _extract_tool_use_ids_from_content(msg.get("content"))
            expected_ids = set(tool_ids) | tool_use_ids
            
            # Tool calls without IDs are invalid for matching
            if not expected_ids:
                if msg.get("tool_calls"):
                    logger.warning("Dropping assistant tool_calls without ids")
                    idx += 1
                    continue
            
            next_idx = idx + 1
            tool_messages: List[Dict[str, Any]] = []
            seen_ids: Set[str] = set()
            valid_sequence = True
            
            # Collect immediate tool messages only
            while next_idx < len(messages) and messages[next_idx].get("role") == "tool":
                tool_msg = messages[next_idx]
                tool_call_id = tool_msg.get("tool_call_id")
                
                if tool_call_id in expected_ids and tool_call_id not in seen_ids:
                    tool_messages.append(tool_msg)
                    seen_ids.add(tool_call_id)
                    next_idx += 1
                    continue
                
                # Unexpected tool message breaks the sequence
                valid_sequence = False
                break
            
            if seen_ids != expected_ids:
                valid_sequence = False
            
            if valid_sequence:
                cleaned.append(msg)
                cleaned.extend(tool_messages)
            else:
                # Fallback: strip tool_use blocks so Anthropic doesn't reject history
                stripped_msg = dict(msg)
                stripped_msg["content"] = _strip_tool_use_blocks(msg.get("content"))
                stripped_msg.pop("tool_calls", None)
                cleaned.append(stripped_msg)
                logger.warning(
                    "Stripped incomplete tool call sequence "
                    f"(expected={len(expected_ids)}, found={len(seen_ids)})"
                )
            
            # Skip over any immediate tool messages we inspected
            idx = next_idx
            continue
        
        # Normal message, keep it
        cleaned.append(msg)
        idx += 1
    
    return cleaned


def reconstruct_message_for_api(msg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert stored message to API format
    
    Args:
        msg: Stored message from database/history
        
    Returns:
        Message formatted for LLM API
    """
    api_msg = {
        "role": msg["role"],
        "content": msg.get("content", "")
    }
    
    # Preserve tool calls for assistant messages
    if msg["role"] == "assistant" and "tool_calls" in msg:
        api_msg["tool_calls"] = msg["tool_calls"]
    
    # Preserve tool call metadata for tool responses
    if msg["role"] == "tool":
        if "tool_call_id" in msg:
            api_msg["tool_call_id"] = msg["tool_call_id"]
        if "name" in msg:
            api_msg["name"] = msg["name"]
    
    return api_msg


def track_pending_tool_calls(
    messages: List[Dict[str, Any]]
) -> Set[str]:
    """
    Track which tool calls are pending responses
    
    Args:
        messages: List of API messages
        
    Returns:
        Set of tool call IDs that don't have responses yet
    """
    pending = set()
    
    for msg in messages:
        # Track tool calls that need responses
        if msg.get("role") == "assistant" and "tool_calls" in msg:
            for tc in msg["tool_calls"]:
                pending.add(tc["id"])
        
        # Mark tool calls as completed
        if msg.get("role") == "tool" and "tool_call_id" in msg:
            pending.discard(msg["tool_call_id"])
    
    return pending


def convert_to_storable_history(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Convert API messages to storable chat history format
    
    - Remove system messages
    - Add timestamps
    - Keep tool_calls and tool results for context
    
    Args:
        messages: List of API messages
        
    Returns:
        List of storable messages
    """
    storable = []
    timestamp = datetime.now().isoformat()
    
    for msg in messages:
        if msg["role"] == "system":
            continue  # Don't store system messages
        
        storable_msg = {
            "role": msg["role"],
            "content": msg.get("content", ""),
            "timestamp": timestamp
        }
        
        # Preserve tool calls
        if "tool_calls" in msg:
            storable_msg["tool_calls"] = msg["tool_calls"]
        
        # Preserve tool call metadata for tool responses
        if msg["role"] == "tool":
            if "tool_call_id" in msg:
                storable_msg["tool_call_id"] = msg["tool_call_id"]
            if "name" in msg:
                storable_msg["name"] = msg.get("name", "")
        
        storable.append(storable_msg)
    
    return storable

