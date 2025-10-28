"""
Main ChatAgent class - clean and focused
"""
from typing import List, Dict, Any, Optional, AsyncGenerator
from litellm import acompletion
import json
import time
from datetime import datetime

from config import Config
from modules.snaptrade_tools import snaptrade_tools, SNAPTRADE_TOOL_DEFINITIONS
from modules.apewisdom_tools import APEWISDOM_TOOL_DEFINITIONS
from modules.insider_trading_tools import INSIDER_TRADING_TOOL_DEFINITIONS
from models.sse import (
    SSEEvent,
    ToolCallStartEvent,
    ToolCallCompleteEvent,
    ThinkingEvent,
    AssistantMessageEvent,
    DoneEvent,
    ErrorEvent
)

from .prompts import build_system_prompt
from .tool_executor import execute_tool
from .stream_handler import accumulate_stream_chunk, stream_content_chunk
from .message_processor import (
    clean_incomplete_tool_calls,
    reconstruct_message_for_api,
    track_pending_tool_calls,
    convert_to_storable_history
)
from .response_builder import build_mock_response_from_stream


# All available tools
ALL_TOOLS = SNAPTRADE_TOOL_DEFINITIONS + APEWISDOM_TOOL_DEFINITIONS + INSIDER_TRADING_TOOL_DEFINITIONS


class ChatAgent:
    """AI Agent for portfolio chatbot using LiteLLM with tool calling support"""
    
    def __init__(self):
        self.model = Config.OPENAI_MODEL
    
    async def process_message(
        self,
        message: str,
        chat_history: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> tuple[str, bool, List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Process a user message and return the agent's response
        
        Args:
            message: User message
            chat_history: Previous conversation
            context: Context variables (not visible to LLM)
            session_id: User session ID
            
        Returns:
            Tuple of (response_text, needs_auth, full_messages, tool_calls_info)
        """
        context = context or {}
        
        try:
            print(f"\n{'='*80}", flush=True)
            print(f"📨 PROCESSING MESSAGE for session: {session_id}", flush=True)
            print(f"📨 Current message: {message}", flush=True)
            print(f"📨 Chat history length: {len(chat_history)}", flush=True)
            print(f"{'='*80}\n", flush=True)
            
            # Build messages for API
            messages = self._build_messages_for_api(message, chat_history, session_id)
            
            # Call LLM
            llm_start = time.time()
            response = await acompletion(
                model=self.model,
                messages=messages,
                api_key=Config.OPENAI_API_KEY,
                tools=ALL_TOOLS,
                reasoning_effort="low",  # GPT-5: Fast mode for lower latency
                caching=True,  # LiteLLM: Enable prompt caching
                seed=42  # OpenAI: Consistent seed helps with caching
            )
            llm_time = int((time.time() - llm_start) * 1000)
            print(f"⏱️ Initial LLM call took {llm_time}ms", flush=True)
            
            # Handle response
            if hasattr(response.choices[0].message, 'tool_calls') and response.choices[0].message.tool_calls:
                tool_start = time.time()
                final_response, needs_auth, tool_calls_info = await self._handle_tool_calls(
                    response, messages, context, session_id
                )
                tool_total_time = int((time.time() - tool_start) * 1000)
                print(f"⏱️ Tool handling (execution + LLM analysis) took {tool_total_time}ms", flush=True)
                storable_messages = convert_to_storable_history(messages)
                return final_response, needs_auth, storable_messages, tool_calls_info
            
            # No tool calls
            storable_messages = convert_to_storable_history(messages)
            response_content = response.choices[0].message.content or "I'm not sure how to respond to that. Could you please rephrase your question?"
            return response_content, False, storable_messages, []
            
        except Exception as e:
            print(f"❌ Error in process_message: {str(e)}", flush=True)
            import traceback
            print(f"❌ Traceback: {traceback.format_exc()}", flush=True)
            return f"I apologize, but I encountered an error: {str(e)}", False, [], []
    
    async def process_message_stream(
        self,
        message: str,
        chat_history: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> AsyncGenerator[SSEEvent, None]:
        """
        Process a user message and stream SSE events as tool calls are made
        
        Args:
            message: User message
            chat_history: Previous conversation
            context: Context variables
            session_id: User session ID
            
        Yields:
            SSEEvent objects containing tool call updates and final response
        """
        context = context or {}
        
        try:
            print(f"\n{'='*80}", flush=True)
            print(f"📨 STREAMING MESSAGE for session: {session_id}", flush=True)
            print(f"📨 Current message: {message}", flush=True)
            print(f"{'='*80}\n", flush=True)
            
            # Build messages for API
            messages = self._build_messages_for_api(message, chat_history, session_id)
            
            # Stream LLM call
            llm_start = time.time()
            print(f"🎬 Streaming initial LLM call...", flush=True)
            
            print(f"🤖 Using model: {self.model}", flush=True)
            stream_response = await acompletion(
                model=self.model,
                messages=messages,
                api_key=Config.OPENAI_API_KEY,
                tools=ALL_TOOLS,
                stream=True,
                stream_options={"include_usage": False},  # Reduce latency
                reasoning_effort="low",  # GPT-5: Use fast thinking mode, not deep reasoning
                temperature=1.0,  # Default, but explicit for speed
                caching=True,  # LiteLLM: Enable prompt caching
                seed=42  # OpenAI: Consistent seed helps with caching
            )
            
            # Stream chunks immediately, detect tool calls as we go
            full_content = ""
            accumulated_tool_calls = []
            is_tool_call = False
            initial_chunk_count = 0
            
            async for chunk in stream_response:
                initial_chunk_count += 1
                full_content, accumulated_tool_calls, is_tool_call = accumulate_stream_chunk(
                    chunk, full_content, accumulated_tool_calls, is_tool_call
                )
                
                # Stream text content immediately as it arrives
                if hasattr(chunk.choices[0], 'delta'):
                    delta = chunk.choices[0].delta
                    if hasattr(delta, 'content') and delta.content:
                        yield SSEEvent(
                            event="assistant_message_delta",
                            data=stream_content_chunk(delta.content)
                        )
            
            llm_time = int((time.time() - llm_start) * 1000)
            print(f"⏱️ Initial LLM call took {llm_time}ms", flush=True)
            
            # Handle based on what we got
            if is_tool_call and accumulated_tool_calls:
                mock_response = build_mock_response_from_stream(full_content, accumulated_tool_calls)
                async for event in self._handle_tool_calls_stream(
                    mock_response, messages, context, session_id
                ):
                    yield event
            else:
                # No tool calls - send final message event
                if not full_content:
                    full_content = "I'm not sure how to respond to that. Could you please rephrase your question?"
                    # Send as delta since we didn't stream anything yet
                    yield SSEEvent(
                        event="assistant_message_delta",
                        data=stream_content_chunk(full_content)
                    )
                
                # Send final complete event
                yield SSEEvent(
                    event="assistant_message",
                    data=AssistantMessageEvent(
                        content=full_content,
                        timestamp=datetime.now().isoformat(),
                        needs_auth=False
                    ).model_dump()
                )
            
            # Send done event
            yield SSEEvent(
                event="done",
                data=DoneEvent().model_dump()
            )
            
        except Exception as e:
            print(f"❌ Error in process_message_stream: {str(e)}", flush=True)
            import traceback
            print(f"❌ Traceback: {traceback.format_exc()}", flush=True)
            
            yield SSEEvent(
                event="error",
                data=ErrorEvent(
                    error=str(e),
                    details=traceback.format_exc()
                ).model_dump()
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
        
        # Check if user just connected
        just_connected = any(
            msg.get("role") == "assistant" and "Successfully connected" in msg.get("content", "")
            for msg in list(reversed(chat_history))[:3]
        )
        
        # Build system prompt with context
        system_prompt = build_system_prompt(has_connection, just_connected)
        
        if just_connected and has_connection:
            print(f"🎯 ACTION REQUIRED: Agent should call get_portfolio now", flush=True)
        
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
    
    async def _handle_tool_calls(
        self,
        initial_response: Any,
        messages: List[Dict[str, Any]],
        context: Dict[str, Any],
        session_id: str
    ) -> tuple[str, bool, List[Dict[str, Any]]]:
        """Handle tool calls from the LLM (non-streaming)"""
        needs_auth = False
        tool_calls_info = []
        
        try:
            # Add assistant's tool call message
            messages.append({
                "role": "assistant",
                "content": initial_response.choices[0].message.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in initial_response.choices[0].message.tool_calls
                ]
            })
            
            # Execute each tool call
            for tool_call in initial_response.choices[0].message.tool_calls:
                tool_exec_start = time.time()
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                result = await execute_tool(function_name, function_args, session_id)
                
                tool_exec_time = int((time.time() - tool_exec_start) * 1000)
                print(f"⏱️ Tool '{function_name}' execution took {tool_exec_time}ms", flush=True)
                
                # Track tool call info
                tool_calls_info.append({
                    "tool_call_id": tool_call.id,
                    "tool_name": function_name,
                    "status": "completed" if result.get("success", True) else "error",
                    "arguments": function_args,
                    "result_data": result,
                    "error": result.get("message") if not result.get("success", True) else None
                })
                
                if result.get("needs_auth") or result.get("action_required") == "show_login_form":
                    needs_auth = True
                
                # Truncate large results
                result_str = self._truncate_tool_result(result)
                
                # Add tool result to messages
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": function_name,
                    "content": result_str
                })
            
            # Get final response from LLM
            print(f"🤔 Sending tool results to LLM for analysis...", flush=True)
            final_llm_start = time.time()
            final_response = await acompletion(
                model=self.model,
                messages=messages,
                api_key=Config.OPENAI_API_KEY,
                tools=ALL_TOOLS,
                reasoning_effort="low",  # GPT-5: Fast mode for lower latency
                caching=True,  # LiteLLM: Enable prompt caching
                seed=42  # OpenAI: Consistent seed helps with caching
            )
            final_llm_time = int((time.time() - final_llm_start) * 1000)
            print(f"⏱️ LLM analysis of tool results took {final_llm_time}ms", flush=True)
            
            # Handle recursive tool calls
            if hasattr(final_response.choices[0].message, 'tool_calls') and final_response.choices[0].message.tool_calls:
                print(f"🔄 LLM requested additional tool calls, handling recursively...", flush=True)
                recursive_response, recursive_needs_auth, recursive_tool_calls = await self._handle_tool_calls(
                    final_response, messages, context, session_id
                )
                needs_auth = needs_auth or recursive_needs_auth
                tool_calls_info.extend(recursive_tool_calls)
                return recursive_response, needs_auth, tool_calls_info
            
            response_content = final_response.choices[0].message.content or "I encountered an issue processing that request. Please try again."
            return response_content, needs_auth, tool_calls_info
            
        except Exception as e:
            print(f"❌ Error in tool processing: {str(e)}", flush=True)
            import traceback
            print(f"❌ Traceback: {traceback.format_exc()}", flush=True)
            return f"I encountered an error while processing tools: {str(e)}", False, []
    
    async def _handle_tool_calls_stream(
        self,
        initial_response: Any,
        messages: List[Dict[str, Any]],
        context: Dict[str, Any],
        session_id: str
    ) -> AsyncGenerator[SSEEvent, None]:
        """Handle tool calls from the LLM (streaming)"""
        needs_auth = False
        
        try:
            # Add assistant's tool call message
            messages.append({
                "role": "assistant",
                "content": initial_response.choices[0].message.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in initial_response.choices[0].message.tool_calls
                ]
            })
            
            # Execute each tool call
            for tool_call in initial_response.choices[0].message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                # Send tool call start event
                yield SSEEvent(
                    event="tool_call_start",
                    data=ToolCallStartEvent(
                        tool_call_id=tool_call.id,
                        tool_name=function_name,
                        arguments=function_args,
                        timestamp=datetime.now().isoformat()
                    ).model_dump()
                )
                
                # Execute tool
                result = await execute_tool(function_name, function_args, session_id)
                
                # Send tool call complete event
                yield SSEEvent(
                    event="tool_call_complete",
                    data=ToolCallCompleteEvent(
                        tool_call_id=tool_call.id,
                        tool_name=function_name,
                        status="completed" if result.get("success", True) else "error",
                        error=result.get("message") if not result.get("success", True) else None,
                        timestamp=datetime.now().isoformat()
                    ).model_dump()
                )
                
                if result.get("needs_auth") or result.get("action_required") == "show_login_form":
                    needs_auth = True
                
                # Truncate and add result
                result_str = self._truncate_tool_result(result)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": function_name,
                    "content": result_str
                })
            
            # Send thinking event
            print(f"🤔 AI is analyzing tool results and generating response...", flush=True)
            yield SSEEvent(
                event="thinking",
                data=ThinkingEvent(message="Analyzing results...").model_dump()
            )
            
            # Stream final response from LLM
            final_llm_start = time.time()
            print(f"🎬 Streaming LLM response...", flush=True)
            print(f"🤖 Using model: {self.model}", flush=True)
            
            stream_response = await acompletion(
                model=self.model,
                messages=messages,
                api_key=Config.OPENAI_API_KEY,
                tools=ALL_TOOLS,
                stream=True,
                stream_options={"include_usage": False},  # Reduce latency
                reasoning_effort="low",  # GPT-5: Fast mode
                caching=True,  # LiteLLM: Enable prompt caching for OpenAI
                seed=42  # OpenAI: Consistent seed helps with caching
            )
            
            # Stream content as it arrives
            full_content = ""
            chunk_count = 0
            async for chunk in stream_response:
                chunk_count += 1
                
                if hasattr(chunk, 'choices') and len(chunk.choices) > 0 and hasattr(chunk.choices[0], 'delta'):
                    delta = chunk.choices[0].delta
                    
                    # Stream content tokens
                    if hasattr(delta, 'content') and delta.content:
                        full_content += delta.content
                        yield SSEEvent(
                            event="assistant_message_delta",
                            data=stream_content_chunk(delta.content)
                        )
                    
                    # Handle edge case: LLM requests more tools (rare)
                    if hasattr(delta, 'tool_calls') and delta.tool_calls:
                        print(f"⚠️ LLM requested additional tools (rare) - not fully supported in streaming", flush=True)
                        break
            
            final_llm_time = int((time.time() - final_llm_start) * 1000)
            print(f"⏱️ LLM response completed in {final_llm_time}ms", flush=True)
            
            # Send final complete event
            yield SSEEvent(
                event="assistant_message",
                data=AssistantMessageEvent(
                    content=full_content,
                    timestamp=datetime.now().isoformat(),
                    needs_auth=needs_auth
                ).model_dump()
            )
            
        except Exception as e:
            print(f"❌ Error in tool processing: {str(e)}", flush=True)
            import traceback
            print(f"❌ Traceback: {traceback.format_exc()}", flush=True)
            
            yield SSEEvent(
                event="error",
                data=ErrorEvent(
                    error=str(e),
                    details=traceback.format_exc()
                ).model_dump()
            )
    
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

