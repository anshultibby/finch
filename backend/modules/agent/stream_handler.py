"""
Streaming response handlers for LLM API calls
"""
from typing import Dict, Any, Tuple, List


def accumulate_stream_chunk(
    chunk: Any,
    full_content: str,
    accumulated_tool_calls: List[Dict[str, Any]],
    is_tool_call: bool
) -> Tuple[str, List[Dict[str, Any]], bool]:
    """
    Process a single stream chunk and accumulate content/tool calls
    
    Args:
        chunk: Stream chunk from LLM API
        full_content: Current accumulated content
        accumulated_tool_calls: Current accumulated tool calls
        is_tool_call: Whether we've detected tool calls
        
    Returns:
        Tuple of (updated_content, updated_tool_calls, updated_is_tool_call)
    """
    if not hasattr(chunk.choices[0], 'delta'):
        return full_content, accumulated_tool_calls, is_tool_call
    
    delta = chunk.choices[0].delta
    
    # Accumulate reasoning content (for o1/o3 models with extended thinking)
    if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
        full_content += delta.reasoning_content
    
    # Accumulate regular content
    if hasattr(delta, 'content') and delta.content:
        full_content += delta.content
    
    # Detect and accumulate tool calls
    if hasattr(delta, 'tool_calls') and delta.tool_calls:
        is_tool_call = True
        for tc_delta in delta.tool_calls:
            tc_index = tc_delta.index
            
            # Ensure we have a slot for this tool call
            while len(accumulated_tool_calls) <= tc_index:
                accumulated_tool_calls.append({
                    "id": "",
                    "type": "function",
                    "function": {"name": "", "arguments": ""}
                })
            
            # Accumulate tool call parts
            if tc_delta.id:
                accumulated_tool_calls[tc_index]["id"] = tc_delta.id
            if hasattr(tc_delta, 'function') and tc_delta.function:
                if tc_delta.function.name:
                    accumulated_tool_calls[tc_index]["function"]["name"] = tc_delta.function.name
                if tc_delta.function.arguments:
                    accumulated_tool_calls[tc_index]["function"]["arguments"] += tc_delta.function.arguments
    
    return full_content, accumulated_tool_calls, is_tool_call


def stream_content_chunk(delta_content: str) -> Dict[str, str]:
    """
    Format a content chunk for SSE streaming
    
    Args:
        delta_content: Text chunk to stream
        
    Returns:
        Dictionary with delta content for SSE event
    """
    return {"delta": delta_content}

