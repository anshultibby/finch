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
import json
import re
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


def _estimate_tokens(text: str) -> int:
    """Rough token estimation: ~4 chars per token"""
    return len(text) // 4




def _is_claude_model(model: str) -> bool:
    """Check if the model is a Claude model that supports prompt caching"""
    m = model.lower()
    return m.startswith("claude") or m.startswith("anthropic/")


def _add_cache_control_to_system(system_content: str, suffix: str = None) -> List[Dict[str, Any]]:
    """
    Convert system prompt to Claude format with cache control.

    The static system prompt gets cache_control so it's cached across requests.
    The optional suffix (e.g. page context) is added as a separate block WITHOUT
    cache_control, so it doesn't bust the cache when it changes.
    """
    blocks = [
        {
            "type": "text",
            "text": system_content,
            "cache_control": {"type": "ephemeral"}
        }
    ]
    if suffix:
        blocks.append({
            "type": "text",
            "text": suffix,
        })
    return blocks


def _add_cache_control_to_tools(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Add cache control to the last tool definition.
    
    IMPORTANT: Tools get their own cache breakpoint, but it comes AFTER system prompt
    in the cache, so system+tools effectively share cache space but tools get the
    actual cache_control marker (they're cached together as one unit).
    
    Args:
        tools: List of tool definitions
        
    Returns:
        Tools list with cache_control added to last tool
    """
    if not tools:
        return tools
    
    # Copy tools to avoid mutating original
    tools_copy = [tool.copy() for tool in tools]
    
    # Add cache_control to the last tool
    # This marks the end of the "static" content (system + tools)
    tools_copy[-1]["cache_control"] = {"type": "ephemeral"}
    
    return tools_copy


def _deep_copy_message(msg: Dict[str, Any]) -> Dict[str, Any]:
    """Deep copy a message to avoid mutating the original."""
    import copy
    return copy.deepcopy(msg)


def _add_cache_control_to_messages(
    messages: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Add cache control breakpoints to conversation history.
    
    IMPORTANT: Returns a deep copy to avoid mutating original messages.
    Cache control should NEVER be persisted to the database.
    
    KEY INSIGHT: Each cache_control breakpoint caches the ENTIRE PREFIX up to that point
    (system + tools + all messages up to the breakpoint).
    
    Strategy per Anthropic docs:
    - System (1) + Tools (1) = 2 breakpoints used
    - We have 2 remaining for messages
    - Place breakpoint at the END of conversation to cache everything
    - Optionally add one more in the middle for very long conversations
    
    Args:
        messages: List of conversation messages
        
    Returns:
        Deep copy of messages with cache_control added at strategic positions
    """
    if not messages:
        return []

    # Deep copy to avoid mutating originals (which get saved to DB)
    messages_copy = [_deep_copy_message(m) for m in messages]
    
    def add_cache_to_message(idx: int):
        """Add cache control to message at given index"""
        if idx < 0 or idx >= len(messages_copy):
            return
            
        msg = messages_copy[idx]
        
        if isinstance(msg.get("content"), str):
            messages_copy[idx]["content"] = [
                {
                    "type": "text",
                    "text": msg["content"],
                    "cache_control": {"type": "ephemeral"}
                }
            ]
        elif isinstance(msg.get("content"), list):
            # Already deep copied, safe to modify
            content_blocks = msg["content"]
            if content_blocks and isinstance(content_blocks[-1], dict):
                content_blocks[-1]["cache_control"] = {"type": "ephemeral"}
    
    msg_count = len(messages)
    
    # Per Anthropic docs: "Always set an explicit cache breakpoint at the end 
    # of your conversation to maximize your chances of cache hits"
    
    # ALWAYS cache at the VERY END - this includes the current user message
    # The only thing NOT cached is the assistant's response (which hasn't been generated yet)
    if msg_count >= 1:
        add_cache_to_message(msg_count - 1)  # Cache up to and including latest message
    
    # For longer conversations, add a stable early breakpoint.
    # IMPORTANT: This must NOT shift as the conversation grows, otherwise
    # the prefix before it gets re-hashed every turn and we get massive
    # cache misses. We anchor at the first user message (index 0 in
    # conversation_messages, which follows the system prompt) so that
    # system + tools + first user message form a stable cached prefix.
    if msg_count > 20:
        add_cache_to_message(0)
    
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
        # Build a system message with cache_control on its content blocks.
        # litellm expects system messages inside the messages array (role="system")
        # — it extracts them and forwards cache_control to the Anthropic API.
        cached_messages: List[Dict[str, Any]] = []
        if system_message:
            suffix = system_message.get("_suffix")
            cached_messages.append({
                "role": "system",
                "content": _add_cache_control_to_system(
                    system_message["content"], suffix=suffix
                ),
            })
            logger.debug(f"  📦 System prompt: ~{len(system_message['content']) // 4:,} tokens (cached)")

        if tools:
            llm_kwargs["tools"] = _add_cache_control_to_tools(tools)
            llm_kwargs["tool_choice"] = "auto"

        cached_messages.extend(_add_cache_control_to_messages(conversation_messages))
        llm_kwargs["messages"] = cached_messages
        logger.debug(f"  📝 Prompt caching with {len(conversation_messages)} messages, cache breakpoints applied")
    else:
        # Non-Claude models or caching disabled: use standard format
        # Merge any dynamic suffix into the system message content
        if system_message and system_message.get("_suffix"):
            merged = {k: v for k, v in messages[0].items() if k != "_suffix"}
            merged["content"] = merged["content"] + "\n\n" + messages[0]["_suffix"]
            messages = [merged] + list(messages[1:])
        llm_kwargs["messages"] = messages
        llm_kwargs["tools"] = tools if tools else None
        llm_kwargs["tool_choice"] = "auto" if tools else None
    
    llm_kwargs["stream"] = True
    # Enable usage tracking in streaming for cache statistics (Claude supports this)
    # Always set this to override any default from llm_config
    llm_kwargs["stream_options"] = {"include_usage": True} if is_claude else {"include_usage": False}
    
    # Stream response
    CHUNK_TIMEOUT_SECONDS = 120

    content = ""
    tool_calls = []
    reasoning_content = ""
    deferred_file_streams: Dict[int, tuple] = {}
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

