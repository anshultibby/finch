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
import time
import traceback as traceback_module
from pathlib import Path
from datetime import datetime
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
    (for conversations longer than 20 messages).
    """
    if not messages:
        return []

    messages_copy = copy.deepcopy(messages)

    _mark_message_cached(messages_copy[-1])

    if len(messages_copy) > 20:
        _mark_message_cached(messages_copy[0])

    return messages_copy


# Track call index per chat for cache diagnostics
_call_counters: Dict[str, int] = {}


def _msg_tokens(msg: Dict[str, Any]) -> int:
    """Rough token estimate for a single message."""
    chars = 0
    content = msg.get("content") or ""
    if isinstance(content, str):
        chars += len(content)
    elif isinstance(content, list):
        for block in content:
            if isinstance(block, dict):
                chars += len(block.get("text", ""))
    for tc in msg.get("tool_calls") or []:
        args = tc.get("function", {}).get("arguments", "")
        chars += len(args) if isinstance(args, str) else 0
    return chars // 4


def _log_cache_diagnostics(
    chat_id: Optional[str],
    call_idx: int,
    messages: List[Dict[str, Any]],
    tools: List[Dict[str, Any]],
    usage_info: Any,
) -> None:
    """Write per-call cache diagnostics to chat_logs for offline analysis."""
    if not chat_id:
        return
    try:
        from .chat_logger import get_chat_log_dir
        backend_dir = Path(__file__).resolve().parent.parent.parent
        log_dir = get_chat_log_dir(chat_id, backend_dir)
        cache_log = log_dir / "cache_diagnostics.jsonl"

        breakpoint_positions = []
        for i, msg in enumerate(messages):
            content = msg.get("content")
            has_bp = False
            if isinstance(content, list):
                has_bp = any(
                    isinstance(b, dict) and "cache_control" in b
                    for b in content
                )
            if has_bp:
                breakpoint_positions.append({
                    "index": i,
                    "role": msg.get("role", "?"),
                    "est_tokens": _msg_tokens(msg),
                    "prefix_tokens": sum(_msg_tokens(messages[j]) for j in range(i + 1)),
                })

        tool_bp = None
        for i, t in enumerate(tools or []):
            if "cache_control" in t:
                tool_bp = {"tool_index": i, "tool_name": t.get("function", {}).get("name", "?")}

        per_msg = [
            {"i": i, "role": m.get("role", "?"), "tokens": _msg_tokens(m)}
            for i, m in enumerate(messages)
        ]

        entry = {
            "ts": datetime.utcnow().isoformat(),
            "call_idx": call_idx,
            "msg_count": len(messages),
            "tool_count": len(tools or []),
            "breakpoints": breakpoint_positions,
            "tool_breakpoint": tool_bp,
            "messages": per_msg,
        }

        if usage_info:
            entry["usage"] = {
                "prompt_tokens": getattr(usage_info, "prompt_tokens", 0),
                "completion_tokens": getattr(usage_info, "completion_tokens", 0),
                "cache_read": getattr(usage_info, "cache_read_input_tokens", 0),
                "cache_creation": getattr(usage_info, "cache_creation_input_tokens", 0),
            }

        cache_log.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_log, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as exc:
        logger.debug(f"Cache diagnostics log failed (non-fatal): {exc}")


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
    
    # Stream response — scale timeout with context size so large conversations
    # don't get killed while the model is still processing.
    # The API may buffer large tool call arguments (e.g. write_chat_file with
    # a big file_content) and deliver them all at once, so we need generous
    # timeouts — especially mid-tool-call.
    estimated_tokens = sum(
        len(str(m.get("content", ""))) // 4 for m in llm_kwargs.get("messages", [])
    )
    if estimated_tokens > 200_000:
        chunk_timeout = 600
    elif estimated_tokens > 100_000:
        chunk_timeout = 300
    else:
        chunk_timeout = 180
    # Even longer when we're mid-tool-call (set dynamically in the loop)
    TOOL_CALL_CHUNK_TIMEOUT = 300

    content = ""
    tool_calls = []
    reasoning_content = ""
    chunk_count = 0
    stream_usage_info = None

    # Stream diagnostics — track state so timeout logs are actionable
    stream_start_time = time.monotonic()
    first_chunk_time: Optional[float] = None
    last_chunk_time: Optional[float] = None
    last_chunk_type = "none"
    content_chars = 0
    reasoning_chars = 0
    tool_call_names: List[str] = []
    tool_call_args_chars = 0
    STALL_WARNING_INTERVALS = [30, 60, 90, 150, 210, 270]

    # Track per-call index for cache diagnostics
    cache_diag_key = chat_id or "unknown"
    _call_counters.setdefault(cache_diag_key, 0)
    _call_counters[cache_diag_key] += 1
    call_idx = _call_counters[cache_diag_key]

    def _stream_state_summary() -> str:
        """Build a diagnostic summary of what the stream has produced so far."""
        if tool_call_names:
            state = f"mid-tool-call ({', '.join(tool_call_names)})"
        elif content_chars > 0:
            state = "mid-content"
        elif reasoning_chars > 0:
            state = "mid-reasoning"
        else:
            state = "no-output"

        elapsed = time.monotonic() - stream_start_time
        since_last = (time.monotonic() - last_chunk_time) if last_chunk_time else elapsed
        avg_gap = (elapsed / chunk_count) if chunk_count > 0 else 0

        lines = [
            f"State: {state}, {content_chars} content chars, {reasoning_chars} reasoning chars, {tool_call_args_chars} tool_arg chars",
            f"Last chunk: {last_chunk_type} ({since_last:.1f}s ago)",
            f"Timeline: {chunk_count} chunks over {elapsed:.1f}s, avg_gap={avg_gap:.2f}s",
        ]
        return "\n      ".join(lines)

    logger.info(f"🔄 Starting LLM stream request (call #{call_idx}, ~{estimated_tokens:,} est. tokens, chunk timeout: {chunk_timeout}s, tool-call timeout: {TOOL_CALL_CHUNK_TIMEOUT}s)...")
    stream_response = await llm_handler.acompletion(**llm_kwargs)
    logger.info("🔄 LLM acompletion returned, starting to iterate chunks...")

    try:
        chunk_iter = stream_response.__aiter__()
        while True:
            try:
                # Use asyncio.wait with a warning task so we can log periodic
                # "still waiting" messages without breaking the main timeout.
                next_chunk_task = asyncio.ensure_future(chunk_iter.__anext__())
                wait_start = time.monotonic()
                warned_intervals = set()

                while True:
                    effective_timeout = TOOL_CALL_CHUNK_TIMEOUT if tool_call_names else chunk_timeout
                    remaining = effective_timeout - (time.monotonic() - wait_start)
                    if remaining <= 0:
                        next_chunk_task.cancel()
                        try:
                            await next_chunk_task
                        except (asyncio.CancelledError, StopAsyncIteration):
                            pass
                        raise asyncio.TimeoutError()

                    next_warning = None
                    for interval in STALL_WARNING_INTERVALS:
                        elapsed_waiting = time.monotonic() - wait_start
                        if interval not in warned_intervals and elapsed_waiting < interval:
                            next_warning = interval - elapsed_waiting
                            break

                    wait_timeout = min(remaining, next_warning) if next_warning else remaining

                    done, _ = await asyncio.wait({next_chunk_task}, timeout=wait_timeout)
                    if done:
                        chunk = next_chunk_task.result()
                        break

                    elapsed_waiting = time.monotonic() - wait_start
                    for interval in STALL_WARNING_INTERVALS:
                        if interval not in warned_intervals and elapsed_waiting >= interval:
                            warned_intervals.add(interval)
                            logger.warning(
                                f"⏳ Waiting for LLM chunk... {elapsed_waiting:.0f}s since last chunk "
                                f"(call #{call_idx}, {_stream_state_summary()})"
                            )

            except StopAsyncIteration:
                break
            except asyncio.TimeoutError:
                effective_timeout = TOOL_CALL_CHUNK_TIMEOUT if tool_call_names else chunk_timeout
                logger.error(
                    f"⏰ LLM stream stalled after {chunk_count} chunks ({effective_timeout}s silence)\n"
                    f"      Call #{call_idx}, ~{estimated_tokens:,} est. tokens\n"
                    f"      {_stream_state_summary()}"
                )
                raise TimeoutError(
                    f"LLM stream stalled after {chunk_count} chunks (no data for {effective_timeout}s). "
                    f"Last chunk type: {last_chunk_type}"
                )

            now = time.monotonic()
            chunk_count += 1
            last_chunk_time = now
            if first_chunk_time is None:
                first_chunk_time = now
                logger.info("🔄 First chunk received from LLM stream")

            if hasattr(chunk, 'usage') and chunk.usage:
                stream_usage_info = chunk.usage

            if not hasattr(chunk, 'choices') or not chunk.choices:
                last_chunk_type = "usage_only" if (hasattr(chunk, 'usage') and chunk.usage) else "empty"
                continue

            delta = chunk.choices[0].delta

            if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                reasoning_content += delta.reasoning_content
                reasoning_chars += len(delta.reasoning_content)
                last_chunk_type = "reasoning"
                yield SSEEvent(
                    event="assistant_message_delta",
                    data=AssistantMessageDeltaEvent(delta=delta.reasoning_content).model_dump()
                )
                if on_content_delta:
                    async for event in on_content_delta(delta.reasoning_content):
                        yield event

            if hasattr(delta, 'content') and delta.content:
                content += delta.content
                content_chars += len(delta.content)
                last_chunk_type = "content"
                yield SSEEvent(
                    event="assistant_message_delta",
                    data=AssistantMessageDeltaEvent(delta=delta.content).model_dump()
                )
                if on_content_delta:
                    async for event in on_content_delta(delta.content):
                        yield event

            if hasattr(delta, 'tool_calls') and delta.tool_calls:
                last_chunk_type = "tool_call"
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
                                tool_call_names.append(tc.function.name)
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
                            tool_call_args_chars += len(tc.function.arguments)

        elapsed = time.monotonic() - stream_start_time
        logger.info(
            f"🔄 LLM stream completed after {chunk_count} chunks in {elapsed:.1f}s "
            f"(content: {content_chars} chars, reasoning: {reasoning_chars} chars, "
            f"tool_calls: {len(tool_calls)} [{', '.join(tool_call_names) or 'none'}])"
        )

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
    
    # Log per-call cache diagnostics for offline analysis
    _log_cache_diagnostics(
        chat_id=chat_id,
        call_idx=call_idx,
        messages=llm_kwargs.get("messages", []),
        tools=llm_kwargs.get("tools", []),
        usage_info=stream_usage_info,
    )

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

