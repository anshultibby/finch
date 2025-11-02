"""
Main ChatAgent class - refactored to use BaseAgent
"""
from typing import List, Dict, Any, Optional, AsyncGenerator
from datetime import datetime
import json
import asyncio

from config import Config
from modules.tools.clients.snaptrade import snaptrade_tools
from modules.tools import tool_registry, tool_runner, ToolStreamHandler
from .context import AgentContext
from models.sse import (
    SSEEvent,
    ToolCallStartEvent,
    ToolCallCompleteEvent,
    ThinkingEvent,
    AssistantMessageEvent,
    DoneEvent,
    ErrorEvent,
    OptionsEvent,
    OptionButton
)

from .prompts import (
    FINCH_SYSTEM_PROMPT,
    AUTH_STATUS_CONNECTED,
    AUTH_STATUS_NOT_CONNECTED
)
from .base_agent import BaseAgent
from .llm_config import LLMConfig
from .message_processor import (
    clean_incomplete_tool_calls,
    track_pending_tool_calls
)

# Import tool_definitions to register all tools
import modules.tools.definitions  # This will auto-register all tools


class ChatAgent(BaseAgent):
    """
    Main user-facing chat agent.
    Inherits from BaseAgent and provides SSE streaming for frontend.
    """
    
    def get_model(self) -> str:
        """Use configured OpenAI model"""
        return Config.OPENAI_MODEL
    
    def get_tool_names(self) -> Optional[List[str]]:
        """
        Main agent uses high-level tools and delegates to specialized agents.
        Individual FMP tools are excluded - use analyze_financials instead.
        """
        return [
            # Portfolio tools
            'get_portfolio',
            'request_brokerage_connection',
            
            # Reddit sentiment
            'get_reddit_trending_stocks',
            'get_reddit_ticker_sentiment',
            'compare_reddit_sentiment',
            
            # Financial analysis (delegated to FMP agent)
            # Note: get_fmp_data (universal FMP tool including insider trading)
            # is NOT included here - main agent delegates via analyze_financials instead
            'analyze_financials',
            
            # Visualization (delegated to plotting agent)
            'create_plot',
            
            # Interactive options
            'present_options'
        ]
    
    def get_system_prompt(self, user_id: Optional[str] = None, **kwargs) -> str:
        """
        Build system prompt with auth status
        
        Args:
            user_id: Used to check auth status
        """
        # Check connection status
        has_connection = snaptrade_tools.has_active_connection(user_id) if user_id else False
        
        # Build system prompt
        system_prompt = FINCH_SYSTEM_PROMPT
        system_prompt += AUTH_STATUS_CONNECTED if has_connection else AUTH_STATUS_NOT_CONNECTED
        
        # Add tool descriptions
        tool_descriptions = tool_registry.get_tool_descriptions_for_prompt()
        system_prompt += f"\n\n{tool_descriptions}"
        
        return system_prompt
    
    async def _execute_tools_step(
        self,
        tool_calls: List[Dict[str, Any]],
        context: AgentContext,
        on_tool_call_start: Optional,
        on_tool_call_complete: Optional
    ):
        """
        Override to add stream_handler for tool event streaming (like present_options)
        """
        # Store events from tools to yield them
        tool_events_queue = []
        
        # Create stream_handler callback that captures events
        async def stream_callback(event: Dict[str, Any]):
            """
            Generic callback that converts ANY tool event to SSE
            Tools can emit any event type and it will be forwarded to frontend
            """
            event_type = event.get("type")
            
            # Forward all tool events as SSE with event name prefixed with "tool_"
            # This allows any tool to stream any type of event
            sse_event = SSEEvent(
                event=f"tool_{event_type}",
                data=event
            )
            tool_events_queue.append(sse_event)
        
        # Create stream handler
        stream_handler = ToolStreamHandler(callback=stream_callback)
        
        # Parse arguments upfront
        parsed_calls = []
        for tc in tool_calls:
            func_name = tc["function"]["name"]
            func_args = json.loads(tc["function"]["arguments"])
            parsed_calls.append({
                "id": tc["id"],
                "name": func_name,
                "args": func_args
            })
        
        # Emit start events for all tools
        if on_tool_call_start:
            for call in parsed_calls:
                async for event in on_tool_call_start({
                    "tool_call_id": call["id"],
                    "tool_name": call["name"],
                    "arguments": call["args"]
                }):
                    yield event
        
        # Execute all tools in parallel
        async def execute_single_tool(call: Dict[str, Any]) -> Dict[str, Any]:
            """Execute one tool and return result with metadata"""
            result = await tool_runner.execute(
                tool_name=call["name"],
                arguments=call["args"],
                user_id=context.user_id,
                resource_manager=context.resource_manager,
                chat_id=context.chat_id,
                stream_handler=stream_handler  # Pass stream handler
            )
            return {
                "tool_call_id": call["id"],
                "tool_name": call["name"],
                "arguments": call["args"],
                "result": result
            }
        
        # Run all tools concurrently
        print(f"🔧 Executing {len(parsed_calls)} tool(s) in parallel", flush=True)
        results = await asyncio.gather(*[execute_single_tool(call) for call in parsed_calls])
        
        # Yield any tool events that were emitted (like options)
        for sse_event in tool_events_queue:
            yield sse_event
        
        # Process results and emit complete events
        tool_messages = []
        for result_data in results:
            result = result_data["result"]
            
            # Notify tool call complete
            if on_tool_call_complete:
                async for event in on_tool_call_complete({
                    "tool_call_id": result_data["tool_call_id"],
                    "tool_name": result_data["tool_name"],
                    "result": result
                }):
                    yield event
            
            # Track tool call info (for parent to access via get_tool_calls_info)
            self._tool_calls_info.append({
                "tool_call_id": result_data["tool_call_id"],
                "tool_name": result_data["tool_name"],
                "status": "completed" if result.get("success", True) else "error",
                "arguments": result_data["arguments"],
                "result_data": result,
                "error": result.get("message") if not result.get("success", True) else None
            })
            
            # Build tool message for conversation
            tool_messages.append({
                "role": "tool",
                "tool_call_id": result_data["tool_call_id"],
                "name": result_data["tool_name"],
                "content": self._truncate_tool_result(result)
            })
        
        # Yield final result (special marker)
        yield ("__tool_messages__", tool_messages)
    
    def _truncate_tool_result(self, result: Dict[str, Any]) -> str:
        """Truncate tool results for conversation (copied from BaseAgent)"""
        import json
        result_str = json.dumps(result)
        max_len = 2000
        if len(result_str) > max_len:
            return result_str[:max_len] + f"... (truncated {len(result_str) - max_len} chars)"
        return result_str
    
    async def process_message_stream(
        self,
        message: str,
        chat_history: List[Dict[str, Any]],
        agent_context: AgentContext  # Always required
    ) -> AsyncGenerator[SSEEvent, None]:
        """
        Stream chat responses using BaseAgent with SSE callbacks
        
        Args:
            message: User message
            chat_history: Previous messages
            agent_context: AgentContext with user_id, chat_id, resource_manager
        """
        needs_auth = [False]  # Mutable to capture in closures
        
        try:
            print(f"\n{'='*80}", flush=True)
            print(f"📨 STREAMING MESSAGE for user: {agent_context.user_id}", flush=True)
            print(f"📨 Current message: {message}", flush=True)
            print(f"{'='*80}\n", flush=True)
            
            # Build initial messages
            initial_messages = self._build_messages_for_api(
                message, chat_history, agent_context
            )
            
            # Define SSE callbacks
            async def on_content_delta(delta: str):
                """Yield SSE event for text delta"""
                yield SSEEvent(
                    event="assistant_message_delta",
                    data={"delta": delta}
                )
            
            async def on_tool_call_start(info: Dict[str, Any]):
                """Yield SSE event for tool call start"""
                yield SSEEvent(
                    event="tool_call_start",
                    data=ToolCallStartEvent(
                        tool_call_id=info["tool_call_id"],
                        tool_name=info["tool_name"],
                        arguments=info["arguments"],
                        timestamp=datetime.now().isoformat()
                    ).model_dump()
                )
            
            async def on_tool_call_complete(info: Dict[str, Any]):
                """Yield SSE event for tool call complete"""
                result = info["result"]
                if result.get("needs_auth"):
                    needs_auth[0] = True
                
                # Regular tool completion event
                yield SSEEvent(
                    event="tool_call_complete",
                    data=ToolCallCompleteEvent(
                        tool_call_id=info["tool_call_id"],
                        tool_name=info["tool_name"],
                        status="completed",
                        timestamp=datetime.now().isoformat()
                    ).model_dump()
                )
            
            async def on_thinking():
                """Yield SSE event for thinking indicator"""
                yield SSEEvent(
                    event="thinking",
                    data=ThinkingEvent(message="Analyzing results...").model_dump()
                )
            
            # Create LLM configuration
            llm_config = LLMConfig.from_config(stream=True)
            
            # Use BaseAgent's streaming loop
            async for event in self.run_tool_loop_streaming(
                initial_messages=initial_messages,
                context=agent_context,
                max_iterations=10,
                llm_config=llm_config,
                on_content_delta=on_content_delta,
                on_tool_call_start=on_tool_call_start,
                on_tool_call_complete=on_tool_call_complete,
                on_thinking=on_thinking
            ):
                # Forward all events from BaseAgent
                yield event
            
            # Yield final assistant message (after streaming completes)
            new_messages = self.get_new_messages()
            if new_messages:
                last_message = new_messages[-1]
                if last_message.get("role") == "assistant":
                    content = last_message.get("content", "")
                    yield SSEEvent(
                        event="assistant_message",
                        data=AssistantMessageEvent(
                            content=content,
                            timestamp=datetime.now().isoformat(),
                            needs_auth=needs_auth[0]
                        ).model_dump()
                    )
            
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
        agent_context: AgentContext
    ) -> List[Dict[str, Any]]:
        """Build message list for LLM API"""
        # Use BaseAgent's build_messages with system prompt
        messages = self.build_messages(
            user_message=message,
            chat_history=chat_history,
            user_id=agent_context.user_id,  # Passed to get_system_prompt
            resource_manager=agent_context.resource_manager  # Passed for resource section
        )
        
        # Clean incomplete tool calls from history
        pending = track_pending_tool_calls(messages)
        if pending:
            messages = clean_incomplete_tool_calls(messages, pending)
        
        return messages

