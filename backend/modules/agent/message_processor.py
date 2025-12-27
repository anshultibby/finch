"""
Message history processing and validation utilities
"""
from typing import List, Dict, Any, Set
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
                    # Malformed JSON - log and replace with empty object
                    logger.warning(
                        f"Malformed tool call arguments for {func.get('name', 'unknown')}: "
                        f"{args_str}... (error: {e})"
                    )
                    func["arguments"] = "{}"
            
            tc_copy["function"] = func
        fixed_calls.append(tc_copy)
    
    return fixed_calls


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

