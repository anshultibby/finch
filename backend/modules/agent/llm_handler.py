"""
LLM Handler - Centralized LLM API interaction with debug logging

Wraps litellm's acompletion to add:
- Debug logging (save requests/responses to disk when enabled)
- Centralized error handling
- Request/response inspection
- OpenTelemetry tracing for performance monitoring
"""
from typing import Dict, Any, Optional, AsyncGenerator
from litellm import acompletion
import json
import os
import time
from datetime import datetime
from pathlib import Path

from config import Config
from utils.logger import get_logger
from utils.tracing import get_tracer, add_span_attributes, add_span_event, record_exception

logger = get_logger(__name__)
tracer = get_tracer(__name__)


class LLMHandler:
    """
    Handler for LLM API calls with optional debug logging.
    
    When DEBUG_LLM_CALLS=true, saves all requests and responses to:
        resources/<user_id>/<timestamp>_<call_number>_request.txt
        resources/<user_id>/<timestamp>_<call_number>_response.txt
    """
    
    def __init__(self, user_id: Optional[str] = None, chat_id: Optional[str] = None):
        """
        Initialize LLM handler
        
        Args:
            user_id: User ID for organizing debug logs
            chat_id: Chat ID for organizing chat logs
        """
        self.user_id = user_id or "unknown"
        self.chat_id = chat_id or "unknown"
        self.call_counter = 0
        self.turn_counter = 0
        self.debug_enabled = Config.DEBUG_LLM_CALLS
        self.chat_log_enabled = Config.DEBUG_CHAT_LOGS
        
        # Create resources directory if debug is enabled
        if self.debug_enabled:
            # Get the backend directory (where this module is located)
            backend_dir = Path(__file__).parent.parent.parent
            self.debug_dir = backend_dir / "resources" / self.user_id
            self.debug_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Debug mode enabled. Logging LLM calls to: {self.debug_dir}")
        
        # Create chat logs directory if chat logging is enabled
        if self.chat_log_enabled:
            backend_dir = Path(__file__).parent.parent.parent
            self.chat_log_dir = backend_dir / "chat_logs" / self.user_id / self.chat_id
            self.chat_log_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Chat logging enabled. Saving conversations to: {self.chat_log_dir}")
    
    async def acompletion(self, **kwargs) -> Any:
        """
        Call LiteLLM's acompletion with optional debug logging and tracing.
        
        Args:
            **kwargs: All arguments passed to litellm.acompletion
            
        Returns:
            LiteLLM completion response (streaming or non-streaming)
        """
        self.call_counter += 1
        call_num = self.call_counter
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Extract model and other metadata for tracing
        model = kwargs.get("model", "unknown")
        is_streaming = kwargs.get("stream", False)
        message_count = len(kwargs.get("messages", []))
        has_tools = "tools" in kwargs and len(kwargs.get("tools", [])) > 0
        
        # Start tracing span
        with tracer.start_as_current_span(f"llm.call") as span:
            start_time = time.time()
            
            # Add attributes for Jaeger
            add_span_attributes({
                "llm.model": model,
                "llm.streaming": is_streaming,
                "llm.message_count": message_count,
                "llm.has_tools": has_tools,
                "llm.call_number": call_num,
                "user.id": self.user_id
            })
            
            add_span_event("LLM request started", {
                "model": model,
                "streaming": is_streaming
            })
            
            # Log request if debug enabled
            if self.debug_enabled:
                self._log_request(timestamp, call_num, kwargs)
            
            try:
                if is_streaming:
                    # For streaming, wrap the async generator to log the complete response
                    return self._acompletion_streaming(timestamp, call_num, kwargs, start_time)
                else:
                    # For non-streaming, just log the response
                    response = await acompletion(**kwargs)
                    duration_ms = (time.time() - start_time) * 1000
                    
                    # Extract token usage if available
                    usage = getattr(response, 'usage', None)
                    if usage:
                        add_span_attributes({
                            "llm.tokens.prompt": getattr(usage, 'prompt_tokens', 0),
                            "llm.tokens.completion": getattr(usage, 'completion_tokens', 0),
                            "llm.tokens.total": getattr(usage, 'total_tokens', 0)
                        })
                    
                    add_span_attributes({"llm.duration_ms": duration_ms})
                    add_span_event("LLM response received", {
                        "duration_ms": duration_ms,
                        "streaming": False
                    })
                    
                    if self.debug_enabled:
                        self._log_response(timestamp, call_num, response)
                    
                    # Log chat conversation if enabled
                    self._log_chat_turn(kwargs, response)
                    
                    logger.info(f"LLM call completed in {duration_ms:.0f}ms (model={model})")
                    return response
                    
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                record_exception(e)
                add_span_attributes({
                    "llm.duration_ms": duration_ms,
                    "error": True
                })
                logger.error(f"LLM call failed after {duration_ms:.0f}ms: {str(e)}")
                raise
    
    async def _acompletion_streaming(
        self, 
        timestamp: str, 
        call_num: int, 
        kwargs: Dict[str, Any],
        start_time: float
    ) -> AsyncGenerator:
        """
        Handle streaming completion with response logging and tracing.
        
        Yields chunks as they arrive, but also accumulates them for logging.
        """
        stream = await acompletion(**kwargs)
        first_chunk_time = None
        chunk_count = 0
        
        accumulated_chunks = []
        
        # Accumulate complete response for chat logging
        accumulated_response = {
            "content": "",
            "reasoning_content": "",
            "tool_calls": {},
            "role": "assistant",
            "finish_reason": None
        }
        
        async for chunk in stream:
            chunk_count += 1
            
            # Track time to first chunk
            if first_chunk_time is None:
                first_chunk_time = time.time()
                ttfb_ms = (first_chunk_time - start_time) * 1000
                add_span_event("First chunk received (TTFB)", {
                    "ttfb_ms": ttfb_ms
                })
                logger.debug(f"LLM first chunk received in {ttfb_ms:.0f}ms")
            
            # Yield chunk immediately for real-time streaming
            yield chunk
            
            # Accumulate for logging
            if self.debug_enabled or self.chat_log_enabled:
                accumulated_chunks.append(chunk)
                
                # Build complete response object from streaming chunks
                if hasattr(chunk, "choices") and len(chunk.choices) > 0:
                    choice = chunk.choices[0]
                    delta = choice.delta
                    
                    # Accumulate regular content
                    if hasattr(delta, "content") and delta.content:
                        accumulated_response["content"] += delta.content
                    
                    # For reasoning models (o1-series), accumulate reasoning content separately
                    if hasattr(delta, "reasoning_content") and delta.reasoning_content:
                        accumulated_response["reasoning_content"] += delta.reasoning_content
                    
                    # Accumulate tool calls
                    if hasattr(delta, "tool_calls") and delta.tool_calls:
                        for tc_delta in delta.tool_calls:
                            idx = tc_delta.index
                            if idx not in accumulated_response["tool_calls"]:
                                accumulated_response["tool_calls"][idx] = {
                                    "id": tc_delta.id or "",
                                    "type": "function",
                                    "function": {
                                        "name": "",
                                        "arguments": ""
                                    }
                                }
                            if tc_delta.id:
                                accumulated_response["tool_calls"][idx]["id"] = tc_delta.id
                            if hasattr(tc_delta, "function") and tc_delta.function:
                                if hasattr(tc_delta.function, "name") and tc_delta.function.name:
                                    accumulated_response["tool_calls"][idx]["function"]["name"] = tc_delta.function.name
                                if hasattr(tc_delta.function, "arguments") and tc_delta.function.arguments:
                                    accumulated_response["tool_calls"][idx]["function"]["arguments"] += tc_delta.function.arguments
                    
                    # Capture finish reason
                    if hasattr(choice, "finish_reason") and choice.finish_reason:
                        accumulated_response["finish_reason"] = choice.finish_reason
        
        # After stream completes, log the full response and timing
        total_duration_ms = (time.time() - start_time) * 1000
        add_span_attributes({
            "llm.duration_ms": total_duration_ms,
            "llm.chunk_count": chunk_count,
            "llm.ttfb_ms": (first_chunk_time - start_time) * 1000 if first_chunk_time else 0
        })
        add_span_event("Stream completed", {
            "duration_ms": total_duration_ms,
            "chunk_count": chunk_count
        })
        logger.info(f"LLM streaming completed in {total_duration_ms:.0f}ms ({chunk_count} chunks)")
        
        if self.debug_enabled:
            logger.debug(f"Writing debug logs to: {self.debug_dir}")
            self._log_streaming_response(timestamp, call_num, accumulated_chunks)
        
        # Log chat turn for streaming responses
        if self.chat_log_enabled:
            content_preview = accumulated_response["content"][:100] if accumulated_response["content"] else "(empty)"
            logger.debug(f"Writing chat log (streaming) - content: '{content_preview}', {len(accumulated_response['tool_calls'])} tool calls")
            self._log_chat_turn_streaming(kwargs, accumulated_response)
    
    def _log_chat_turn(self, kwargs: Dict[str, Any], response: Any = None):
        """Log chat conversation turn to JSON for analysis"""
        if not self.chat_log_enabled:
            return
        
        try:
            self.turn_counter += 1
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_turn_{self.turn_counter:03d}.json"
            filepath = self.chat_log_dir / filename
            
            messages = kwargs.get("messages", [])
            
            # Extract user message (last message before this call)
            user_message = ""
            for msg in reversed(messages):
                if msg.get("role") == "user":
                    user_message = msg.get("content", "")
                    break
            
            # Extract assistant response if available
            assistant_message = ""
            tool_calls = []
            if response:
                if hasattr(response, "choices") and len(response.choices) > 0:
                    message = response.choices[0].message
                    assistant_message = message.content or ""
                    if hasattr(message, "tool_calls") and message.tool_calls:
                        for tc in message.tool_calls:
                            tool_calls.append({
                                "id": tc.id,
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            })
            
            log_data = {
                "timestamp": datetime.now().isoformat(),
                "user_id": self.user_id,
                "chat_id": self.chat_id,
                "turn_number": self.turn_counter,
                "model": kwargs.get("model", "unknown"),
                "user_message": user_message,
                "assistant_message": assistant_message,
                "tool_calls": tool_calls,
                "full_conversation": messages,
                "config": {
                    "temperature": kwargs.get("temperature"),
                    "max_tokens": kwargs.get("max_tokens"),
                    "reasoning_effort": kwargs.get("reasoning_effort"),
                }
            }
            
            with open(filepath, "w") as f:
                json.dump(log_data, f, indent=2)
            
            logger.info(f"💾 Saved chat turn to: {filename}")
        
        except Exception as e:
            logger.error(f"Failed to log chat turn: {e}", exc_info=True)
    
    def _log_chat_turn_streaming(self, kwargs: Dict[str, Any], accumulated_response: Dict[str, Any]):
        """Log chat conversation turn from streaming response - saves complete raw response"""
        if not self.chat_log_enabled:
            return
        
        content_len = len(accumulated_response.get("content", ""))
        reasoning_len = len(accumulated_response.get("reasoning_content", ""))
        tool_call_count = len(accumulated_response.get("tool_calls", {}))
        logger.debug(f"_log_chat_turn_streaming called: content={content_len} chars, reasoning={reasoning_len} chars, tool_calls={tool_call_count}")
        
        try:
            self.turn_counter += 1
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_turn_{self.turn_counter:03d}.json"
            filepath = self.chat_log_dir / filename
            
            messages = kwargs.get("messages", [])
            
            # Extract user message (last message before this call)
            user_message = ""
            for msg in reversed(messages):
                if msg.get("role") == "user":
                    user_message = msg.get("content", "")
                    break
            
            # Convert tool_calls dict to list format (for JSON serialization)
            tool_calls_list = []
            for tc_data in accumulated_response.get("tool_calls", {}).values():
                if tc_data.get("id"):
                    tool_calls_list.append(tc_data)
            
            log_data = {
                "timestamp": datetime.now().isoformat(),
                "user_id": self.user_id,
                "chat_id": self.chat_id,
                "turn_number": self.turn_counter,
                "model": kwargs.get("model", "unknown"),
                "streaming": True,
                "user_message": user_message,
                
                # Full raw response (everything the model returned)
                "assistant_response": {
                    "role": accumulated_response.get("role", "assistant"),
                    "content": accumulated_response.get("content", ""),
                    "reasoning_content": accumulated_response.get("reasoning_content", ""),
                    "tool_calls": tool_calls_list if tool_calls_list else None,
                    "finish_reason": accumulated_response.get("finish_reason")
                },
                
                # Also keep backward-compatible top-level fields
                "assistant_message": accumulated_response.get("content", ""),
                "reasoning_trace": accumulated_response.get("reasoning_content", ""),
                "tool_calls": tool_calls_list,
                
                # Full conversation context
                "full_conversation": messages,
                
                # Config used for this call
                "config": {
                    "temperature": kwargs.get("temperature"),
                    "max_tokens": kwargs.get("max_tokens"),
                    "reasoning_effort": kwargs.get("reasoning_effort"),
                    "stream": kwargs.get("stream", False),
                }
            }
            
            with open(filepath, "w") as f:
                json.dump(log_data, f, indent=2)
            
            logger.info(f"💾 Saved chat turn (streaming) to: {filename}")
        
        except Exception as e:
            logger.error(f"Failed to log chat turn (streaming): {e}", exc_info=True)
    
    def _log_request(self, timestamp: str, call_num: int, kwargs: Dict[str, Any]):
        """Log the LLM request to disk"""
        try:
            request_file = self.debug_dir / f"{timestamp}_{call_num:03d}_request.txt"
            
            # Create a clean version of kwargs for logging
            log_kwargs = kwargs.copy()
            
            # Format messages nicely
            messages = log_kwargs.get("messages", [])
            tools = log_kwargs.get("tools", [])
            
            with open(request_file, "w") as f:
                f.write("=" * 80 + "\n")
                f.write(f"LLM REQUEST #{call_num}\n")
                f.write(f"User: {self.user_id}\n")
                f.write(f"Timestamp: {timestamp}\n")
                f.write("=" * 80 + "\n\n")
                
                # Model and config
                f.write(f"Model: {log_kwargs.get('model', 'unknown')}\n")
                f.write(f"Temperature: {log_kwargs.get('temperature', 'default')}\n")
                f.write(f"Max Tokens: {log_kwargs.get('max_tokens', 'default')}\n")
                f.write(f"Stream: {log_kwargs.get('stream', False)}\n")
                f.write(f"Tool Choice: {log_kwargs.get('tool_choice', 'none')}\n")
                f.write("\n")
                
                # Messages
                f.write("-" * 80 + "\n")
                f.write("MESSAGES:\n")
                f.write("-" * 80 + "\n")
                for i, msg in enumerate(messages):
                    f.write(f"\n[Message {i+1}] Role: {msg.get('role', 'unknown')}\n")
                    
                    if "content" in msg and msg["content"]:
                        f.write(f"Content:\n{msg['content']}\n")
                    
                    if "tool_calls" in msg:
                        f.write(f"Tool Calls: {len(msg['tool_calls'])}\n")
                        for tc in msg["tool_calls"]:
                            f.write(f"  - {tc.get('function', {}).get('name', 'unknown')}\n")
                            args = tc.get('function', {}).get('arguments', '{}')
                            f.write(f"    Args: {args}\n")
                    
                    if msg.get("role") == "tool":
                        f.write(f"Tool Call ID: {msg.get('tool_call_id', 'unknown')}\n")
                        f.write(f"Tool Response:\n{msg.get('content', '')}\n")
                
                # Tools available
                if tools:
                    f.write("\n" + "-" * 80 + "\n")
                    f.write("AVAILABLE TOOLS:\n")
                    f.write("-" * 80 + "\n")
                    for tool in tools:
                        func = tool.get("function", {})
                        f.write(f"\n{func.get('name', 'unknown')}:\n")
                        f.write(f"  {func.get('description', 'No description')}\n")
                        params = func.get('parameters', {})
                        if params.get('properties'):
                            f.write(f"  Parameters: {list(params['properties'].keys())}\n")
            
            logger.debug(f"Saved request to: {request_file.name}")
        
        except Exception as e:
            logger.warning(f"Failed to log request: {e}")
    
    def _log_response(self, timestamp: str, call_num: int, response: Any):
        """Log the LLM response (non-streaming) to disk"""
        try:
            response_file = self.debug_dir / f"{timestamp}_{call_num:03d}_response.txt"
            
            with open(response_file, "w") as f:
                f.write("=" * 80 + "\n")
                f.write(f"LLM RESPONSE #{call_num}\n")
                f.write(f"User: {self.user_id}\n")
                f.write(f"Timestamp: {timestamp}\n")
                f.write("=" * 80 + "\n\n")
                
                message = response.choices[0].message
                
                # Content
                if message.content:
                    f.write("CONTENT:\n")
                    f.write("-" * 80 + "\n")
                    f.write(f"{message.content}\n\n")
                
                # Tool calls
                if hasattr(message, "tool_calls") and message.tool_calls:
                    f.write("TOOL CALLS:\n")
                    f.write("-" * 80 + "\n")
                    for tc in message.tool_calls:
                        f.write(f"\nTool: {tc.function.name}\n")
                        f.write(f"ID: {tc.id}\n")
                        f.write(f"Arguments:\n")
                        # Pretty print JSON arguments
                        try:
                            args = json.loads(tc.function.arguments)
                            f.write(json.dumps(args, indent=2))
                        except:
                            f.write(tc.function.arguments)
                        f.write("\n")
                
                # Usage stats
                if hasattr(response, "usage"):
                    f.write("\n" + "-" * 80 + "\n")
                    f.write("USAGE:\n")
                    f.write("-" * 80 + "\n")
                    f.write(f"Prompt tokens: {response.usage.prompt_tokens}\n")
                    f.write(f"Completion tokens: {response.usage.completion_tokens}\n")
                    f.write(f"Total tokens: {response.usage.total_tokens}\n")
            
            logger.debug(f"Saved response to: {response_file.name}")
        
        except Exception as e:
            logger.warning(f"Failed to log response: {e}")
    
    def _log_streaming_response(self, timestamp: str, call_num: int, chunks: list):
        """Log accumulated streaming response to disk"""
        try:
            response_file = self.debug_dir / f"{timestamp}_{call_num:03d}_response.txt"
            
            with open(response_file, "w") as f:
                f.write("=" * 80 + "\n")
                f.write(f"LLM RESPONSE #{call_num} (STREAMING)\n")
                f.write(f"User: {self.user_id}\n")
                f.write(f"Timestamp: {timestamp}\n")
                f.write("=" * 80 + "\n\n")
                
                # Accumulate content and tool calls
                content = ""
                reasoning_content = ""
                tool_calls = {}
                
                for chunk in chunks:
                    if not hasattr(chunk, "choices") or not chunk.choices:
                        continue
                    
                    delta = chunk.choices[0].delta
                    
                    # Accumulate reasoning content (for o1/o3 models with extended thinking)
                    if hasattr(delta, "reasoning_content") and delta.reasoning_content:
                        reasoning_content += delta.reasoning_content
                    
                    # Accumulate regular content
                    if hasattr(delta, "content") and delta.content:
                        content += delta.content
                    
                    # Accumulate tool calls
                    if hasattr(delta, "tool_calls") and delta.tool_calls:
                        for tc_delta in delta.tool_calls:
                            idx = tc_delta.index
                            
                            if idx not in tool_calls:
                                tool_calls[idx] = {
                                    "id": "",
                                    "name": "",
                                    "arguments": ""
                                }
                            
                            if hasattr(tc_delta, "id") and tc_delta.id:
                                tool_calls[idx]["id"] = tc_delta.id
                            
                            if hasattr(tc_delta, "function"):
                                if hasattr(tc_delta.function, "name") and tc_delta.function.name:
                                    tool_calls[idx]["name"] = tc_delta.function.name
                                
                                if hasattr(tc_delta.function, "arguments") and tc_delta.function.arguments:
                                    tool_calls[idx]["arguments"] += tc_delta.function.arguments
                
                # Write reasoning content (for o1/o3 models)
                if reasoning_content:
                    f.write("REASONING CONTENT (Extended Thinking):\n")
                    f.write("-" * 80 + "\n")
                    f.write(f"{reasoning_content}\n\n")
                
                # Write regular content
                if content:
                    f.write("CONTENT:\n")
                    f.write("-" * 80 + "\n")
                    f.write(f"{content}\n\n")
                
                # Write tool calls
                if tool_calls:
                    f.write("TOOL CALLS:\n")
                    f.write("-" * 80 + "\n")
                    for idx, tc in sorted(tool_calls.items()):
                        f.write(f"\nTool: {tc['name']}\n")
                        f.write(f"ID: {tc['id']}\n")
                        f.write(f"Arguments:\n")
                        # Pretty print JSON arguments
                        try:
                            args = json.loads(tc['arguments'])
                            f.write(json.dumps(args, indent=2))
                        except:
                            f.write(tc['arguments'])
                        f.write("\n")
                
                f.write("\n" + "-" * 80 + "\n")
                f.write(f"Total chunks received: {len(chunks)}\n")
            
            logger.debug(f"Saved streaming response to: {response_file.name}")
        
        except Exception as e:
            logger.warning(f"Failed to log streaming response: {e}")

