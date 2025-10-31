"""
Main ChatAgent class - clean and focused
"""
from typing import List, Dict, Any, Optional, AsyncGenerator
from litellm import acompletion
import json
import time
from datetime import datetime

from config import Config
from modules.snaptrade_tools import snaptrade_tools
from modules.tools import tool_registry
from models.sse import (
    SSEEvent,
    ToolCallStartEvent,
    ToolCallCompleteEvent,
    ThinkingEvent,
    AssistantMessageEvent,
    DoneEvent,
    ErrorEvent
)

from .prompts import (
    FINCH_SYSTEM_PROMPT,
    AUTH_STATUS_CONNECTED,
    AUTH_STATUS_NOT_CONNECTED
)
from .tool_executor import execute_tool
from .stream_handler import accumulate_stream_chunk, stream_content_chunk
from .message_processor import (
    clean_incomplete_tool_calls,
    reconstruct_message_for_api,
    track_pending_tool_calls,
    convert_to_storable_history
)
from .response_builder import build_mock_response_from_stream

# Import tool_definitions to register all tools
import modules.tool_definitions  # This will auto-register all tools


class ChatAgent:
    """AI Agent for portfolio chatbot using LiteLLM with tool calling support"""
    
    def __init__(self):
        self.model = Config.OPENAI_MODEL
        self._last_messages = []  # Store messages from last stream
        self._initial_messages_len = 0  # Track where new messages start
        self._tool_calls_info = []  # Store tool call execution info
    
    def get_new_messages(self) -> List[Dict[str, Any]]:
        """Get the new messages from the last stream (for saving to DB)"""
        return self._last_messages[self._initial_messages_len:]
    
    def get_tool_calls_info(self) -> List[Dict[str, Any]]:
        """Get tool call execution information from the last stream"""
        return self._tool_calls_info
    
    async def process_message_stream(
        self,
        message: str,
        chat_history: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> AsyncGenerator[SSEEvent, None]:
        """
        Simple chat loop with streaming:
        1. Call LLM, stream response
        2. If tool calls → execute tools, add to history, loop back to step 1
        3. If text → show to user, done
        """
        context = context or {}
        needs_auth = False
        
        try:
            print(f"\n{'='*80}", flush=True)
            print(f"📨 STREAMING MESSAGE for session: {session_id}", flush=True)
            print(f"📨 Current message: {message}", flush=True)
            print(f"{'='*80}\n", flush=True)
            
            # Build initial messages
            initial_messages = self._build_messages_for_api(message, chat_history, session_id)
            messages = initial_messages.copy()
            
            # Store for later retrieval (only new messages, not including system/history/user)
            self._last_messages = messages
            self._initial_messages_len = len(initial_messages)
            
            # Reset tool calls info for this interaction
            self._tool_calls_info = []
            
            # Simple loop: LLM → tools → LLM → ... → final text
            while True:
                # Get all tool schemas from registry
                tools = tool_registry.get_all_schemas()
                
                # Call LLM and stream
                stream_response = await acompletion(
                    model=self.model,
                    messages=messages,
                    api_key=Config.OPENAI_API_KEY,
                    tools=tools,
                    stream=True,
                    stream_options={"include_usage": False},
                    reasoning_effort="low",
                    caching=True,
                    seed=42
                )
                
                # Stream response and collect tool calls
                content = ""
                tool_calls = []
                
                async for chunk in stream_response:
                    if hasattr(chunk, 'choices') and len(chunk.choices) > 0 and hasattr(chunk.choices[0], 'delta'):
                        delta = chunk.choices[0].delta
                        
                        # Stream text
                        if hasattr(delta, 'content') and delta.content:
                            content += delta.content
                            yield SSEEvent(
                                event="assistant_message_delta",
                                data={"delta": delta.content}
                            )
                        
                        # Collect tool calls
                        if hasattr(delta, 'tool_calls') and delta.tool_calls:
                            for tc in delta.tool_calls:
                                idx = tc.index
                                while len(tool_calls) <= idx:
                                    tool_calls.append({
                                        "id": "",
                                        "type": "function",  # Required by OpenAI
                                        "function": {"name": "", "arguments": ""}
                                    })
                                if tc.id:
                                    tool_calls[idx]["id"] = tc.id
                                if hasattr(tc, 'function') and tc.function:
                                    if tc.function.name:
                                        tool_calls[idx]["function"]["name"] = tc.function.name
                                    if tc.function.arguments:
                                        tool_calls[idx]["function"]["arguments"] += tc.function.arguments
                
                # If text response → done
                if not tool_calls:
                    if not content:
                        content = "I'm not sure how to respond."
                    
                    yield SSEEvent(
                        event="assistant_message",
                        data=AssistantMessageEvent(
                            content=content,
                            timestamp=datetime.now().isoformat(),
                            needs_auth=needs_auth
                        ).model_dump()
                    )
                    break  # Exit loop
                
                # If tool calls → execute and loop
                messages.append({"role": "assistant", "content": content or "", "tool_calls": tool_calls})
                
                for tc in tool_calls:
                    func_name = tc["function"]["name"]
                    func_args = json.loads(tc["function"]["arguments"])
                    
                    # Notify frontend
                    yield SSEEvent(
                        event="tool_call_start",
                        data=ToolCallStartEvent(
                            tool_call_id=tc["id"],
                            tool_name=func_name,
                            arguments=func_args,
                            timestamp=datetime.now().isoformat()
                        ).model_dump()
                    )
                    
                    # Execute
                    result = await execute_tool(func_name, func_args, session_id)
                    
                    if result.get("needs_auth"):
                        needs_auth = True
                    
                    # Track tool call info for resource creation
                    self._tool_calls_info.append({
                        "tool_call_id": tc["id"],
                        "tool_name": func_name,
                        "status": "completed" if result.get("success", True) else "error",
                        "arguments": func_args,
                        "result_data": result,
                        "error": result.get("message") if not result.get("success", True) else None
                    })
                    
                    # Notify completion
                    yield SSEEvent(
                        event="tool_call_complete",
                        data=ToolCallCompleteEvent(
                            tool_call_id=tc["id"],
                            tool_name=func_name,
                            status="completed",
                            timestamp=datetime.now().isoformat()
                        ).model_dump()
                    )
                    
                    # Add result to messages
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "name": func_name,
                        "content": self._truncate_tool_result(result)
                    })
                
                # Show thinking indicator before looping
                yield SSEEvent(
                    event="thinking",
                    data=ThinkingEvent(message="Analyzing results...").model_dump()
                )
                # Loop continues...
            
            # Done
            yield SSEEvent(
                event="done",
                data=DoneEvent().model_dump()
            )
            
        except Exception as e:
            print(f"❌ Error: {str(e)}", flush=True)
            import traceback
            print(f"❌ Traceback: {traceback.format_exc()}", flush=True)
            
            yield SSEEvent(
                event="error",
                data=ErrorEvent(error=str(e), details=traceback.format_exc()).model_dump()
            )
    
    def _build_messages_for_api(
        self,
        message: str,
        chat_history: List[Dict[str, Any]],
        session_id: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Build message list for LLM API"""
        # Check connection status
        has_connection = snaptrade_tools.has_active_connection(session_id) if session_id else False
        
        # Build system prompt using simple string concatenation
        system_prompt = FINCH_SYSTEM_PROMPT
        system_prompt += AUTH_STATUS_CONNECTED if has_connection else AUTH_STATUS_NOT_CONNECTED
        
        # Add tool descriptions to prompt (best practice for function calling)
        tool_descriptions = tool_registry.get_tool_descriptions_for_prompt()
        system_prompt += f"\n\n{tool_descriptions}"
        
        # Start with system message
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add chat history
        for msg in chat_history:
            if msg["role"] in ["user", "assistant", "tool"]:
                messages.append(reconstruct_message_for_api(msg))
        
        # Clean incomplete tool calls
        pending = track_pending_tool_calls(messages)
        if pending:
            messages = clean_incomplete_tool_calls(messages, pending)
        
        # Add current message
        messages.append({"role": "user", "content": message})
        
        return messages
    
    def _truncate_tool_result(self, result: Dict[str, Any]) -> str:
        """Truncate large tool results to avoid overwhelming the LLM"""
        try:
            result_str = json.dumps(result)
        except Exception as e:
            print(f"❌ Error serializing tool result: {e}", flush=True)
            return json.dumps({"success": False, "error": f"Failed to serialize: {str(e)}"})
        
        max_size = 50000  # 50KB limit
        
        if len(result_str) > max_size:
            print(f"⚠️ Tool result too large ({len(result_str)} bytes), truncating to {max_size} bytes", flush=True)
            
            # Try intelligent truncation for portfolio activity
            if "portfolio_activity" in result and isinstance(result["portfolio_activity"], dict):
                original_count = len(result["portfolio_activity"])
                truncated_activity = dict(list(result["portfolio_activity"].items())[:10])
                result["portfolio_activity"] = truncated_activity
                result["_truncated"] = f"Showing top 10 of {original_count} tickers with activity"
                print(f"📊 Truncated portfolio activity from {original_count} to 10 tickers", flush=True)
                result_str = json.dumps(result)
            
            # Hard truncate if still too large
            if len(result_str) > max_size:
                result_str = result_str[:max_size] + '... [TRUNCATED]"}'
                print(f"⚠️ Hard truncated to {max_size} bytes", flush=True)
        
        return result_str

