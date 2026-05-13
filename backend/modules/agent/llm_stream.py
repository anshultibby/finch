"""
Standalone LLM streaming functions - clean separation from agent logic

**Streaming Architecture:**

Event Flow: LLM Stream → Agent → Chat Service → Client
            
Phase 1: LLM Response
  - assistant_message_delta (text content streams as LLM generates)
  
Phase 2: File Content (AFTER LLM completes)
  - tool_call_streaming (file content streams for write_chat_file/replace_in_chat_file)
  
Phase 3: Tool Execution (handled by agent/executor)
  - tool_call_start
  - tool_call_complete
  - tools_end

This ordering is critical to prevent message reordering bugs where file content
interleaves with assistant messages during multi-turn conversations.
"""
from typing import List, Dict, Any, Optional, AsyncGenerator, Callable
import copy
import json
import asyncio
import traceback as traceback_module
from schemas.sse import SSEEvent, LLMStartEvent, LLMEndEvent, AssistantMessageDeltaEvent, ToolCallStreamingEvent, ToolCallDetectedEvent
from .llm_handler import LLMHandler
from .llm_config import LLMConfig
from .message_processor import validate_and_fix_tool_calls, enforce_tool_call_sequence
from utils.logger import get_logger

logger = get_logger(__name__)

# Tools that should have their file content streamed to the UI
# These are streamed AFTER LLM completes to prevent interleaving with message deltas
FILE_STREAMING_TOOLS = {'write_chat_file', 'replace_in_chat_file'}


def _is_claude_model(model: str) -> bool:
    """Check if the model is a Claude model that supports prompt caching"""
    m = model.lower()
    return m.startswith("claude") or m.startswith("anthropic/")


def _add_cache_control_to_tools(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Add cache_control to the last tool definition to mark end of static content."""
    if not tools:
        return tools
    tools_copy = [tool.copy() for tool in tools]
    tools_copy[-1]["cache_control"] = {"type": "ephemeral"}
    return tools_copy


def _mark_message_cached(msg: Dict[str, Any]) -> None:
    """Add cache_control breakpoint to a message (mutates in place)."""
    content = msg.get("content")
    if isinstance(content, str):
        msg["content"] = [
            {"type": "text", "text": content, "cache_control": {"type": "ephemeral"}}
        ]
    elif isinstance(content, list) and content and isinstance(content[-1], dict):
        content[-1]["cache_control"] = {"type": "ephemeral"}


def _add_cache_control_to_messages(
    messages: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Add cache control breakpoints to conversation history.

    Returns a deep copy to avoid mutating originals (which get saved to DB).
    Places a breakpoint at the last message (always) and the first message
    (for conversations longer than 20 messages) to maximize cache hits.
    """
    if not messages:
        return []

    messages_copy = copy.deepcopy(messages)

    # Always cache the last message — caches entire prefix up to this point
    _mark_message_cached(messages_copy[-1])

    # For longer conversations, anchor a stable early breakpoint
    if len(messages_copy) > 20:
        _mark_message_cached(messages_copy[0])

    return messages_copy


async def stream_llm_response(
    messages: List[Dict[str, Any]],
    tools: List[Dict[str, Any]],
    llm_config: LLMConfig,
    user_id: str,
    chat_id: Optional[str] = None,
    on_content_delta: Optional[Callable[[str], AsyncGenerator[SSEEvent, None]]] = None,
    chat_logger = None
) -> AsyncGenerator[SSEEvent, None]:
    """
    Stream LLM response and yield SSE events with robust ordering guarantees.
    
    **Event Ordering (Critical for UI):**
    1. `llm_start` - LLM call begins
    2. `assistant_message_delta` events - Assistant text content streams
    3. `tool_call_streaming` events - File content streams (AFTER assistant message completes)
    4. `llm_end` - LLM call completes with full tool calls
    
    This ordering prevents file content from interleaving with assistant messages,
    which was causing message reordering bugs in multi-turn conversations.
    
    Supports Claude prompt caching for cost optimization:
    - System prompt is always cached
    - Tool definitions are cached together
    - Older conversation history is cached (keeping recent messages fresh)
    
    Args:
        messages: Messages to send to LLM (must include system message as first message)
        tools: Available tools
        llm_config: LLM configuration
        user_id: User ID for logging
        chat_id: Chat ID for organizing chat logs
        on_content_delta: Optional callback for content deltas
        chat_logger: Optional ChatLogger to use for conversation logging
        
    Yields:
        SSEEvent objects (llm_start, assistant_message_delta, tool_call_streaming, llm_end)
    """
    # Ensure tool call sequences are valid for Anthropic before streaming
    messages = enforce_tool_call_sequence(messages)
    
    # Emit start event
    yield SSEEvent(
        event="llm_start",
        data=LLMStartEvent(message_count=len(messages)).model_dump()
    )
    
    # Create LLM handler with chat_id for proper log organization
    # If chat_logger is provided, use it for separate executor logging
    if chat_logger:
        llm_handler = LLMHandler(
            user_id=user_id,
            chat_id=chat_id,
            agent_type=chat_logger.agent_type,
            agent_id=chat_logger.agent_id,
            chat_logger=chat_logger
        )
    else:
        llm_handler = LLMHandler(user_id=user_id, chat_id=chat_id)
    
    # Build kwargs for LiteLLM
    llm_kwargs = llm_config.to_litellm_kwargs()
    
    # Extract system message (first message should be system)
    system_message = None
    conversation_messages = messages
    if messages and messages[0].get("role") == "system":
        system_message = messages[0]
        conversation_messages = messages[1:]
    
    # Apply prompt caching for Claude models
    is_claude = _is_claude_model(llm_kwargs["model"])
    
    if is_claude and llm_config.caching:
        # litellm expects system messages inside the messages array (role="system")
        # — it extracts them and forwards cache_control to the Anthropic API.
        cached_messages: List[Dict[str, Any]] = []
        if system_message:
            cached_messages.append({
                "role": "system",
                "content": [{"type": "text", "text": system_message["content"], "cache_control": {"type": "ephemeral"}}],
            })
        cached_messages.extend(_add_cache_control_to_messages(conversation_messages))
        llm_kwargs["messages"] = cached_messages

        if tools:
            llm_kwargs["tools"] = _add_cache_control_to_tools(tools)
            llm_kwargs["tool_choice"] = "auto"

        logger.debug(f"  📝 Prompt caching with {len(conversation_messages)} messages, cache breakpoints applied")
    else:
        llm_kwargs["messages"] = messages
        if tools:
            llm_kwargs["tools"] = tools
            llm_kwargs["tool_choice"] = "auto"
    
    llm_kwargs["stream"] = True
    # Enable usage tracking in streaming for cache statistics (Claude supports this)
    # Always set this to override any default from llm_config
    llm_kwargs["stream_options"] = {"include_usage": True} if is_claude else {"include_usage": False}
    
    # Stream response
    CHUNK_TIMEOUT_SECONDS = 120

    content = ""
    tool_calls = []
    reasoning_content = ""
    chunk_count = 0

    logger.info("🔄 Starting LLM stream request...")
    stream_response = await llm_handler.acompletion(**llm_kwargs)
    logger.info("🔄 LLM acompletion returned, starting to iterate chunks...")

    try:
        chunk_iter = stream_response.__aiter__()
        while True:
            try:
                chunk = await asyncio.wait_for(chunk_iter.__anext__(), timeout=CHUNK_TIMEOUT_SECONDS)
            except StopAsyncIteration:
                break
            except asyncio.TimeoutError:
                logger.error(f"⏰ LLM stream stalled - no chunk received in {CHUNK_TIMEOUT_SECONDS}s after {chunk_count} chunks")
                raise TimeoutError(f"LLM stream stalled after {chunk_count} chunks (no data for {CHUNK_TIMEOUT_SECONDS}s)")
            chunk_count += 1
            if chunk_count == 1:
                logger.info("🔄 First chunk received from LLM stream")
            if not hasattr(chunk, 'choices') or not chunk.choices:
                continue

            delta = chunk.choices[0].delta

            if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                reasoning_content += delta.reasoning_content
                yield SSEEvent(
                    event="assistant_message_delta",
                    data=AssistantMessageDeltaEvent(delta=delta.reasoning_content).model_dump()
                )
                if on_content_delta:
                    async for event in on_content_delta(delta.reasoning_content):
                        yield event

            if hasattr(delta, 'content') and delta.content:
                content += delta.content
                yield SSEEvent(
                    event="assistant_message_delta",
                    data=AssistantMessageDeltaEvent(delta=delta.content).model_dump()
                )
                if on_content_delta:
                    async for event in on_content_delta(delta.content):
                        yield event

            if hasattr(delta, 'tool_calls') and delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    while len(tool_calls) <= idx:
                        tool_calls.append({
                            "id": "",
                            "type": "function",
                            "function": {"name": "", "arguments": ""}
                        })
                    if tc.id:
                        tool_calls[idx]["id"] = tc.id
                    if hasattr(tc, 'function') and tc.function:
                        if tc.function.name:
                            if not tool_calls[idx]["function"]["name"]:
                                yield SSEEvent(
                                    event="tool_call_detected",
                                    data=ToolCallDetectedEvent(
                                        tool_call_id=tool_calls[idx]["id"],
                                        tool_name=tc.function.name,
                                        index=idx,
                                    ).model_dump()
                                )
                            tool_calls[idx]["function"]["name"] = tc.function.name

                        if tc.function.arguments:
                            tool_calls[idx]["function"]["arguments"] += tc.function.arguments

        logger.info(f"🔄 LLM stream completed after {chunk_count} chunks (content: {len(content)} chars, tool_calls: {len(tool_calls)})")

    except Exception as e:
        logger.error(f"❌ Error during LLM streaming: {e}")
        logger.error(f"Traceback: {traceback_module.format_exc()}")
        raise
    
    # Validate tool calls before emitting - fix any malformed JSON arguments
    # This prevents litellm from failing when sending these back to Anthropic
    validated_tool_calls = validate_and_fix_tool_calls(tool_calls)
    
    # Extract and stream file content NOW (after LLM completes, before llm_end)
    # This ensures clean separation: assistant message → file content → tool execution
    for idx, tc in enumerate(validated_tool_calls):
        tool_name = tc.get("function", {}).get("name")
        if tool_name in FILE_STREAMING_TOOLS:
            tool_call_id = tc.get("id")
            args_str = tc.get("function", {}).get("arguments", "{}")
            
            try:
                args = json.loads(args_str)
                filename = args.get("filename", "unknown")
                
                # Extract file content based on tool
                if tool_name == "write_chat_file":
                    file_content = args.get("file_content", "")
                elif tool_name == "replace_in_chat_file":
                    file_content = args.get("new_str", "")
                else:
                    file_content = ""
                
                # Stream the file content in reasonable chunks (not too small, not too large)
                if file_content:
                    chunk_size = 500  # Characters per chunk for smooth streaming
                    for i in range(0, len(file_content), chunk_size):
                        chunk = file_content[i:i+chunk_size]
                        is_final = (i + chunk_size) >= len(file_content)
                        
                        yield SSEEvent(
                            event="tool_call_streaming",
                            data=ToolCallStreamingEvent(
                                tool_call_id=tool_call_id,
                                tool_name=tool_name,
                                arguments_delta="",  # Empty since we're streaming extracted content
                                filename=filename,
                                file_content_delta=chunk
                            ).model_dump()
                        )
                        # Small delay for smooth streaming
                        if not is_final:
                            await asyncio.sleep(0.01)
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"Could not extract file content for streaming: {e}")
    
    # Emit end event
    logger.info(f"🔄 Emitting llm_end event (content_length={len(content)}, tool_calls_count={len(validated_tool_calls)})")
    yield SSEEvent(
        event="llm_end",
        data=LLMEndEvent(
            content=content,
            tool_calls=validated_tool_calls
        ).model_dump()
    )
    logger.info("🔄 llm_end event yielded successfully")

