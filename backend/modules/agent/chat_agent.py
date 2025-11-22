"""
Main ChatAgent class - refactored to use BaseAgent
"""
from typing import List, Dict, Any, Optional, AsyncGenerator, TYPE_CHECKING
from datetime import datetime
import json
import asyncio

if TYPE_CHECKING:
    from models.chat_history import ChatHistory

from config import Config
from modules.tools.clients.snaptrade import snaptrade_tools
from modules.tools import tool_registry, tool_runner
from modules.tools.stream_handler import ToolStreamHandler
from .context import AgentContext
from models.sse import (
    SSEEvent,
    ToolCallStartEvent,
    ToolCallCompleteEvent,
    ThinkingEvent,
    AssistantMessageEvent,
    DoneEvent,
    ErrorEvent,
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
from utils.logger import get_logger

logger = get_logger(__name__)

# Import tool_definitions to register all tools
import modules.tools.definitions  # This will auto-register all tools


class ChatAgent(BaseAgent):
    """
    Main user-facing chat agent.
    Inherits from BaseAgent and provides SSE streaming for frontend.
    """
    
    def get_model(self) -> str:
        """Use GPT-5 for main chat agent"""
        return Config.OPENAI_MODEL
    
    def get_tool_names(self) -> Optional[List[str]]:
        """
        Main agent has access to all tools directly.
        """
        return [
            # Portfolio tools
            'get_portfolio',
            'request_brokerage_connection',
            
            # Reddit sentiment
            'get_reddit_trending_stocks',
            'get_reddit_ticker_sentiment',
            'compare_reddit_sentiment',
            
            # Financial analysis (FMP)
            'get_fmp_data',
            
            # Visualization
            'create_chart',
            
            # Interactive options
            'present_options'
        ]
    
    def get_system_prompt(self, **kwargs) -> str:
        """
        Return fixed system prompt.
        No dynamic content - auth status and tool availability are handled at runtime.
        """
        return FINCH_SYSTEM_PROMPT
    
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
        # Use asyncio.Queue for real-time event streaming
        tool_events_queue = asyncio.Queue()
        
        # Create stream_handler factory for each tool (to add metadata)
        def create_stream_handler(tool_call_id: str, tool_name: str) -> ToolStreamHandler:
            """Create a stream handler for a specific tool call"""
            async def stream_callback(event: Dict[str, Any]):
                """
                Generic callback that converts ANY tool event to SSE
                Tools can emit any event type and it will be forwarded to frontend
                """
                event_type = event.get("type")
                sse_event = SSEEvent(
                    event=f"tool_{event_type}",
                    data=event
                )
                # Put event in queue for real-time streaming
                await tool_events_queue.put(sse_event)
            
            return ToolStreamHandler(callback=stream_callback, tool_call_id=tool_call_id, tool_name=tool_name)
        
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
            # Create a stream handler specifically for this tool
            stream_handler = create_stream_handler(call["id"], call["name"])
            
            result = await tool_runner.execute(
                tool_name=call["name"],
                arguments=call["args"],
                user_id=context.user_id,
                resource_manager=context.resource_manager,
                chat_id=context.chat_id,
                stream_handler=stream_handler  # Pass tool-specific stream handler
            )
            return {
                "tool_call_id": call["id"],
                "tool_name": call["name"],
                "arguments": call["args"],
                "result": result
            }
        
        # Run all tools concurrently while streaming events in real-time
        logger.info(f"Executing {len(parsed_calls)} tool(s) in parallel")
        
        # Wrap gather in an async function so we can use create_task
        async def run_all_tools():
            return await asyncio.gather(*[execute_single_tool(call) for call in parsed_calls])
        
        # Create task for executing all tools
        tools_task = asyncio.create_task(run_all_tools())
        
        # Stream events in real-time as they arrive
        while True:
            # Check if tools are done
            if tools_task.done():
                # Drain remaining events from queue
                while not tool_events_queue.empty():
                    try:
                        sse_event = tool_events_queue.get_nowait()
                        yield sse_event
                    except asyncio.QueueEmpty:
                        break
                # Get results and break
                results = await tools_task
                break
            
            # Try to get events from queue with timeout
            try:
                sse_event = await asyncio.wait_for(tool_events_queue.get(), timeout=0.1)
                yield sse_event
            except asyncio.TimeoutError:
                # No events yet, continue waiting
                continue
        
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
        chat_history: "ChatHistory",  # Use ChatHistory model
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
                tool_name = info["tool_name"]
                
                # Emit detailed status based on tool type
                status_message = f"Calling {tool_name.replace('_', ' ')}..."
                if tool_name == "get_fmp_data":
                    args = info.get("arguments", {})
                    endpoint = args.get("endpoint", "")
                    params = args.get("params", {})
                    symbol = params.get("symbol", "") if params else ""
                    endpoint_readable = endpoint.replace("_", " ").title()
                    if symbol:
                        status_message = f"Fetching {endpoint_readable} for {symbol}..."
                    else:
                        status_message = f"Fetching {endpoint_readable}..."
                elif tool_name == "get_portfolio":
                    status_message = "Retrieving your portfolio..."
                elif tool_name == "create_chart":
                    status_message = "Creating visualization..."
                
                # Emit status
                yield SSEEvent(
                    event="tool_status",
                    data={
                        "status": "executing",
                        "message": status_message,
                        "timestamp": datetime.now().isoformat()
                    }
                )
                
                # Emit standard tool_call_start
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
                tool_name = info["tool_name"]
                
                if result.get("needs_auth"):
                    needs_auth[0] = True
                
                # Emit completion status
                if result.get("success"):
                    completion_message = f"✓ {tool_name.replace('_', ' ').title()} completed"
                    
                    # Add specific details if available
                    if tool_name == "get_fmp_data":
                        data = result.get("data", [])
                        if isinstance(data, list) and len(data) > 0:
                            completion_message = f"✓ Retrieved {len(data)} records"
                    elif tool_name == "get_portfolio":
                        completion_message = "✓ Portfolio retrieved"
                    elif tool_name == "create_chart":
                        title = result.get("title", "Chart")
                        completion_message = f"✓ Created: {title}"
                    
                    yield SSEEvent(
                        event="tool_status",
                        data={
                            "status": "completed",
                            "message": completion_message,
                            "timestamp": datetime.now().isoformat()
                        }
                    )
                else:
                    error_msg = result.get("error", "Unknown error")
                    yield SSEEvent(
                        event="tool_status",
                        data={
                            "status": "error",
                            "message": f"✗ {tool_name}: {error_msg}",
                            "timestamp": datetime.now().isoformat()
                        }
                    )
                
                # Regular tool completion event
                yield SSEEvent(
                    event="tool_call_complete",
                    data=ToolCallCompleteEvent(
                        tool_call_id=info["tool_call_id"],
                        tool_name=info["tool_name"],
                        status="completed" if result.get("success") else "error",
                        timestamp=datetime.now().isoformat()
                    ).model_dump()
                )
            
            async def on_thinking():
                """Yield SSE event for thinking indicator"""
                # More descriptive thinking message based on context
                yield SSEEvent(
                    event="thinking",
                    data=ThinkingEvent(message="Processing results and formulating response...").model_dump()
                )
                
                # Also emit as status
                yield SSEEvent(
                    event="tool_status",
                    data={
                        "status": "thinking",
                        "message": "Analyzing data and preparing response...",
                        "timestamp": datetime.now().isoformat()
                    }
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
                if last_message.role == "assistant":
                    yield SSEEvent(
                        event="assistant_message",
                        data=AssistantMessageEvent(
                            content=last_message.content or "",
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
            logger.error(f"Error: {str(e)}")
            import traceback
            logger.debug(f"Traceback: {traceback.format_exc()}")
            
            yield SSEEvent(
                event="error",
                data=ErrorEvent(error=str(e), details=traceback.format_exc()).model_dump()
            )
    
    def _build_messages_for_api(
        self,
        message: str,
        chat_history: "ChatHistory",
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

