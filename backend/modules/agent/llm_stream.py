"""
Standalone LLM streaming functions - clean separation from agent logic
"""
from typing import List, Dict, Any, Optional, AsyncGenerator, Callable
import json
import re
from models.sse import SSEEvent, LLMStartEvent, LLMEndEvent, AssistantMessageDeltaEvent, ToolCallStreamingEvent
from .llm_handler import LLMHandler
from .llm_config import LLMConfig
from .message_processor import validate_and_fix_tool_calls
from utils.logger import get_logger

logger = get_logger(__name__)

# Tools that should have their file content streamed during LLM generation
FILE_STREAMING_TOOLS = {'write_chat_file', 'replace_in_chat_file'}


def _get_file_type_from_filename(filename: str) -> str:
    """Determine file type from filename extension."""
    if filename.endswith('.py'):
        return "python"
    elif filename.endswith('.md'):
        return "markdown"
    elif filename.endswith('.csv'):
        return "csv"
    elif filename.endswith('.json'):
        return "json"
    elif filename.endswith('.html'):
        return "html"
    elif filename.endswith('.js'):
        return "javascript"
    elif filename.endswith('.ts'):
        return "typescript"
    elif filename.endswith('.tsx'):
        return "typescript"
    elif filename.endswith('.jsx'):
        return "javascript"
    return "text"


class FileContentExtractor:
    """
    Incrementally extracts file content from streaming JSON arguments.
    
    For write_chat_file: extracts 'file_content' field
    For replace_in_chat_file: extracts 'new_str' field
    """
    
    def __init__(self, tool_name: str):
        self.tool_name = tool_name
        self.arguments_buffer = ""
        self.filename: Optional[str] = None
        self.content_field = "file_content" if tool_name == "write_chat_file" else "new_str"
        self.content_start_pos: Optional[int] = None
        self.last_extracted_len = 0
        self.in_content_string = False
        self.escape_next = False
    
    def add_chunk(self, chunk: str) -> Optional[str]:
        """
        Add a chunk of JSON arguments and return any new file content extracted.
        
        Returns None if no new content, or the delta string if new content found.
        """
        self.arguments_buffer += chunk
        
        # Try to find filename if we don't have it yet
        if self.filename is None:
            self._try_extract_filename()
        
        # Try to extract content delta
        return self._extract_content_delta()
    
    def _try_extract_filename(self):
        """Try to extract filename from the buffer."""
        # Look for "filename": "value" pattern
        match = re.search(r'"filename"\s*:\s*"([^"]*)"', self.arguments_buffer)
        if match:
            self.filename = match.group(1)
    
    def _extract_content_delta(self) -> Optional[str]:
        """Extract any new content from the content field."""
        # Look for the start of our content field if we haven't found it
        if self.content_start_pos is None:
            # Pattern: "file_content": " or "new_str": "
            pattern = f'"{self.content_field}"\\s*:\\s*"'
            match = re.search(pattern, self.arguments_buffer)
            if match:
                self.content_start_pos = match.end()
                self.last_extracted_len = 0
                self.in_content_string = True
        
        if self.content_start_pos is None:
            return None
        
        # Extract content from the string, handling escapes
        content_portion = self.arguments_buffer[self.content_start_pos:]
        
        # Find the end of the string (unescaped quote)
        extracted = []
        i = 0
        while i < len(content_portion):
            char = content_portion[i]
            
            if self.escape_next:
                # Handle escape sequences
                if char == 'n':
                    extracted.append('\n')
                elif char == 't':
                    extracted.append('\t')
                elif char == 'r':
                    extracted.append('\r')
                elif char == '\\':
                    extracted.append('\\')
                elif char == '"':
                    extracted.append('"')
                else:
                    extracted.append(char)
                self.escape_next = False
            elif char == '\\':
                self.escape_next = True
            elif char == '"':
                # End of string - but don't include the closing quote
                self.in_content_string = False
                break
            else:
                extracted.append(char)
            
            i += 1
        
        full_content = ''.join(extracted)
        
        # Return only the new portion
        if len(full_content) > self.last_extracted_len:
            delta = full_content[self.last_extracted_len:]
            self.last_extracted_len = len(full_content)
            return delta
        
        return None


def _estimate_tokens(text: str) -> int:
    """Rough token estimation: ~4 chars per token"""
    return len(text) // 4




def _is_claude_model(model: str) -> bool:
    """Check if the model is a Claude model that supports prompt caching"""
    return model.lower().startswith("claude")


def _add_cache_control_to_system(system_content: str) -> List[Dict[str, Any]]:
    """
    Convert system prompt to Claude format with cache control.
    
    For Claude models, the system parameter must be a list of content blocks,
    and we add cache_control to the last block to cache the entire system prompt.
    
    Args:
        system_content: System prompt string
        
    Returns:
        List with single text block containing cache_control
    """
    return [
        {
            "type": "text",
            "text": system_content,
            "cache_control": {"type": "ephemeral"}
        }
    ]


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
    if len(messages) <= 1:
        return [_deep_copy_message(m) for m in messages]
    
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
    
    # For longer conversations (>20 messages), add a midpoint breakpoint
    # This helps with the 20-block lookback window limitation
    if msg_count > 20:
        # Add a breakpoint around the middle to ensure earlier content can be cached
        mid_position = msg_count // 2
        add_cache_to_message(mid_position)
    
    return messages_copy


async def stream_llm_response(
    messages: List[Dict[str, Any]],
    tools: List[Dict[str, Any]],
    llm_config: LLMConfig,
    user_id: str,
    chat_id: Optional[str] = None,
    on_content_delta: Optional[Callable[[str], AsyncGenerator[SSEEvent, None]]] = None
) -> AsyncGenerator[SSEEvent, None]:
    """
    Stream LLM response and yield SSE events.
    
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
        
    Yields:
        SSEEvent objects (llm_start, content deltas, llm_end)
    """
    # Emit start event
    yield SSEEvent(
        event="llm_start",
        data=LLMStartEvent(message_count=len(messages)).model_dump()
    )
    
    # Create LLM handler with chat_id for proper log organization
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
        logger.debug("🔄 Applying Claude prompt caching (MAXIMUM strategy)")
        
        # Cache system prompt (converted to block format for Claude, but NO cache_control here)
        system_tokens_estimate = len(system_message["content"]) // 4 if system_message else 0
        if system_message:
            # DON'T add cache_control to system - it will be covered by tools cache breakpoint
            llm_kwargs["system"] = _add_cache_control_to_system(system_message["content"])
            logger.debug(f"  📦 System prompt: ~{system_tokens_estimate:,} tokens (cached with tools)")
        
        # Cache tools - this is the ONLY breakpoint for static content (system + tools together)
        if tools:
            llm_kwargs["tools"] = _add_cache_control_to_tools(tools)
            llm_kwargs["tool_choice"] = "auto"
            tools_tokens_estimate = sum(len(str(tool)) for tool in tools) // 4
            logger.debug(f"  📌 Breakpoint 1: Tools ({len(tools)} tools, ~{tools_tokens_estimate:,} tokens)")
            logger.debug(f"     ↳ This caches system + tools together (~{system_tokens_estimate + tools_tokens_estimate:,} total)")
        
        # Cache conversation history with ALL remaining breakpoints (3 for messages!)
        original_message_count = len(conversation_messages)
        llm_kwargs["messages"] = _add_cache_control_to_messages(conversation_messages)
        
        # Count cache breakpoints in messages and show what's being cached
        breakpoints = []
        for i, msg in enumerate(llm_kwargs["messages"]):
            content = msg.get("content")
            has_cache = False
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and "cache_control" in block:
                        has_cache = True
                        break
            if has_cache:
                role = msg.get("role", "unknown")
                # Estimate token count
                content_str = str(content) if isinstance(content, str) else str(content)
                tokens_est = len(content_str) // 4
                breakpoints.append(f"msg{i}({role}, ~{tokens_est:,}tok)")
        
        if breakpoints:
            for i, bp in enumerate(breakpoints, start=2):
                logger.debug(f"  📌 Breakpoint {i}: {bp}")
            logger.debug(f"     ↳ Total: {len(breakpoints)} message breakpoint(s) covering {original_message_count} messages")
        else:
            logger.debug(f"  📌 No message breakpoints yet (conversation too short)")
        
        total_breakpoints = (1 if system_message else 0) + (1 if tools else 0) + len(breakpoints)
        logger.debug(f"  ✅ Using {total_breakpoints}/4 cache breakpoints")
        logger.debug(f"  📝 Strategy: Prefix caching - each breakpoint caches everything before it")
    else:
        # Non-Claude models or caching disabled: use standard format
        llm_kwargs["messages"] = messages
        llm_kwargs["tools"] = tools if tools else None
        llm_kwargs["tool_choice"] = "auto" if tools else None
    
    llm_kwargs["stream"] = True
    # Enable usage tracking in streaming for cache statistics (Claude supports this)
    # Always set this to override any default from llm_config
    llm_kwargs["stream_options"] = {"include_usage": True} if is_claude else {"include_usage": False}
    
    # Stream response
    stream_response = await llm_handler.acompletion(**llm_kwargs)
    
    # Accumulate response
    content = ""
    tool_calls = []
    reasoning_content = ""
    
    # Track file content extractors for streaming file tools
    # Key: tool call index, Value: FileContentExtractor
    file_extractors: Dict[int, FileContentExtractor] = {}
    
    # Process stream
    async for chunk in stream_response:
        if not hasattr(chunk, 'choices') or not chunk.choices:
            continue
            
        delta = chunk.choices[0].delta
        
        # Handle reasoning content (o1/o3 models)
        if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
            reasoning_content += delta.reasoning_content
            yield SSEEvent(
                event="assistant_message_delta",
                data=AssistantMessageDeltaEvent(delta=delta.reasoning_content).model_dump()
            )
            if on_content_delta:
                async for event in on_content_delta(delta.reasoning_content):
                    yield event
        
        # Handle regular content
        if hasattr(delta, 'content') and delta.content:
            content += delta.content
            yield SSEEvent(
                event="assistant_message_delta",
                data=AssistantMessageDeltaEvent(delta=delta.content).model_dump()
            )
            if on_content_delta:
                async for event in on_content_delta(delta.content):
                    yield event
        
        # Accumulate tool calls and stream file content for file tools
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
                        tool_calls[idx]["function"]["name"] = tc.function.name
                        # Initialize file extractor for file streaming tools
                        if tc.function.name in FILE_STREAMING_TOOLS and idx not in file_extractors:
                            file_extractors[idx] = FileContentExtractor(tc.function.name)
                    
                    if tc.function.arguments:
                        tool_calls[idx]["function"]["arguments"] += tc.function.arguments
                        
                        # Stream file content if this is a file tool
                        if idx in file_extractors:
                            extractor = file_extractors[idx]
                            content_delta = extractor.add_chunk(tc.function.arguments)
                            
                            if content_delta:
                                # Emit file content streaming event
                                tool_call_id = tool_calls[idx]["id"]
                                tool_name = tool_calls[idx]["function"]["name"]
                                filename = extractor.filename or "unknown"
                                file_type = _get_file_type_from_filename(filename) if extractor.filename else "text"
                                
                                yield SSEEvent(
                                    event="tool_call_streaming",
                                    data=ToolCallStreamingEvent(
                                        tool_call_id=tool_call_id,
                                        tool_name=tool_name,
                                        arguments_delta=tc.function.arguments,
                                        filename=filename,
                                        file_content_delta=content_delta
                                    ).model_dump()
                                )
    
    # Validate tool calls before emitting - fix any malformed JSON arguments
    # This prevents litellm from failing when sending these back to Anthropic
    validated_tool_calls = validate_and_fix_tool_calls(tool_calls)
    
    # Emit end event
    yield SSEEvent(
        event="llm_end",
        data=LLMEndEvent(
            content=content,
            tool_calls=validated_tool_calls
        ).model_dump()
    )

