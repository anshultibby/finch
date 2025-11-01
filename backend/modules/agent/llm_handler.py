"""
LLM Handler - Centralized LLM API interaction with debug logging

Wraps litellm's acompletion to add:
- Debug logging (save requests/responses to disk when enabled)
- Centralized error handling
- Request/response inspection
"""
from typing import Dict, Any, Optional, AsyncGenerator
from litellm import acompletion
import json
import os
from datetime import datetime
from pathlib import Path

from config import Config


class LLMHandler:
    """
    Handler for LLM API calls with optional debug logging.
    
    When DEBUG_LLM_CALLS=true, saves all requests and responses to:
        resources/<user_id>/<timestamp>_<call_number>_request.txt
        resources/<user_id>/<timestamp>_<call_number>_response.txt
    """
    
    def __init__(self, user_id: Optional[str] = None):
        """
        Initialize LLM handler
        
        Args:
            user_id: User ID for organizing debug logs
        """
        self.user_id = user_id or "unknown"
        self.call_counter = 0
        self.debug_enabled = Config.DEBUG_LLM_CALLS
        
        # Create resources directory if debug is enabled
        if self.debug_enabled:
            # Get the backend directory (where this module is located)
            backend_dir = Path(__file__).parent.parent.parent
            self.debug_dir = backend_dir / "resources" / self.user_id
            self.debug_dir.mkdir(parents=True, exist_ok=True)
            print(f"🐛 Debug mode enabled. Logging LLM calls to: {self.debug_dir}", flush=True)
    
    async def acompletion(self, **kwargs) -> Any:
        """
        Call LiteLLM's acompletion with optional debug logging.
        
        Args:
            **kwargs: All arguments passed to litellm.acompletion
            
        Returns:
            LiteLLM completion response (streaming or non-streaming)
        """
        self.call_counter += 1
        call_num = self.call_counter
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Log request if debug enabled
        if self.debug_enabled:
            self._log_request(timestamp, call_num, kwargs)
        
        # Determine if streaming
        is_streaming = kwargs.get("stream", False)
        
        if is_streaming:
            # For streaming, wrap the async generator to log the complete response
            return self._acompletion_streaming(timestamp, call_num, kwargs)
        else:
            # For non-streaming, just log the response
            response = await acompletion(**kwargs)
            
            if self.debug_enabled:
                self._log_response(timestamp, call_num, response)
            
            return response
    
    async def _acompletion_streaming(
        self, 
        timestamp: str, 
        call_num: int, 
        kwargs: Dict[str, Any]
    ) -> AsyncGenerator:
        """
        Handle streaming completion with response logging.
        
        Yields chunks as they arrive, but also accumulates them for logging.
        """
        stream = await acompletion(**kwargs)
        
        accumulated_chunks = []
        
        async for chunk in stream:
            # Yield chunk immediately for real-time streaming
            yield chunk
            
            # Accumulate for logging
            if self.debug_enabled:
                accumulated_chunks.append(chunk)
        
        # After stream completes, log the full response
        if self.debug_enabled:
            self._log_streaming_response(timestamp, call_num, accumulated_chunks)
    
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
            
            print(f"📝 Saved request to: {request_file.name}", flush=True)
        
        except Exception as e:
            print(f"⚠️ Failed to log request: {e}", flush=True)
    
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
            
            print(f"📝 Saved response to: {response_file.name}", flush=True)
        
        except Exception as e:
            print(f"⚠️ Failed to log response: {e}", flush=True)
    
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
                tool_calls = {}
                
                for chunk in chunks:
                    if not hasattr(chunk, "choices") or not chunk.choices:
                        continue
                    
                    delta = chunk.choices[0].delta
                    
                    # Accumulate content
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
                
                # Write content
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
            
            print(f"📝 Saved streaming response to: {response_file.name}", flush=True)
        
        except Exception as e:
            print(f"⚠️ Failed to log streaming response: {e}", flush=True)

