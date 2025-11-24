"""
Base Agent class - reusable agent logic for main and specialized agents
"""
from typing import List, Dict, Any, Optional, AsyncGenerator, Callable
import json
import asyncio

from modules.tools import (
    tool_registry, 
    ToolExecutor, 
    ToolCallRequest, 
    TruncationPolicy
)
from models.sse import SSEEvent, ToolsEndEvent, ThinkingEvent, AssistantMessageEvent, DoneEvent, ErrorEvent
from models.chat_history import ChatHistory, ChatMessage as HistoryChatMessage
from .llm_config import LLMConfig
from .llm_stream import stream_llm_response
from .context import AgentContext
from utils.logger import get_logger
from .tracing_utils import AgentTracer
from datetime import datetime
import traceback as traceback_module

logger = get_logger(__name__)


class BaseAgent:
    """
    Agent with common LLM interaction logic.
    
    Configuration-based approach (no subclassing needed).
    Pass system_prompt, tools, model, and streaming config to __init__.
    """
    
    def __init__(
        self,
        context: AgentContext,
        system_prompt: str,
        model: str,
        tool_names: Optional[List[str]] = None,
        enable_tool_streaming: bool = False
    ):
        """
        Initialize the agent with configuration.
        
        Args:
            context: AgentContext with user_id, chat_id, resource_manager
            system_prompt: System prompt for this agent
            model: Model name (e.g., "gpt-4", "gpt-4o-mini")
            tool_names: List of tool names (None = all tools, [] = no tools)
            enable_tool_streaming: Whether tools emit real-time events
        """
        self.context = context
        self.system_prompt = system_prompt
        self.model = model
        self.tool_names = tool_names
        self.enable_tool_streaming = enable_tool_streaming
        
        # Agent doesn't own history - it just tracks new messages for this turn
        self._new_messages: List[HistoryChatMessage] = []
        self._tool_calls_info: List[Dict[str, Any]] = []
        self._agent_tracer = AgentTracer(
            agent_name=self.__class__.__name__,
            user_id=context.user_id,
            chat_id=context.chat_id,
            model=model
        )
        # Create tool executor with simple 10K char truncation
        self._tool_executor = ToolExecutor(
            truncation_policy=TruncationPolicy(max_chars=10000)
        )
    
    def get_new_messages(self) -> List[HistoryChatMessage]:
        """
        Get the new messages from the last interaction (for saving to DB).
        
        Returns:
            List of ChatMessage objects added during this interaction
        """
        return self._new_messages
    
    def get_tool_calls_info(self) -> List[Dict[str, Any]]:
        """Get tool call execution information from the last interaction"""
        return self._tool_calls_info
    
    async def _execute_tools_step(
        self,
        tool_calls: List[Dict[str, Any]],
        context: AgentContext
    ):
        """
        Execute all tool calls and yield events - clean streaming design.
        
        Uses pure event pattern:
        - Yields SSEEvent objects throughout execution
        - ToolExecutor handles ALL streaming internally
        - Final 'tools_end' event includes both tool messages AND execution results
        - No double execution needed
        """
        # Parse OpenAI tool calls into ToolCallRequest objects
        tool_call_requests = []
        for tc in tool_calls:
            func_name = tc["function"]["name"]
            func_args = json.loads(tc["function"]["arguments"])
            tool_call_requests.append(
                ToolCallRequest(
                    id=tc["id"],
                    name=func_name,
                    arguments=func_args
                )
            )
        
        # Use ToolExecutor - yields SSE events directly (simple!)
        async for event in self._tool_executor.execute_batch_streaming(
            tool_calls=tool_call_requests,
            context=context,
            enable_tool_streaming=self.enable_tool_streaming
        ):
            # Extract execution results from tools_end event to populate tracking info
            if event.event == "tools_end":
                execution_results = event.data.get("execution_results", [])
                # Populate tool_calls_info directly from execution results (no double execution!)
                self._tool_calls_info.extend(execution_results)
            
            # Forward all events
            yield event
    
    async def run_tool_loop_streaming(
        self,
        initial_messages: List[Dict[str, Any]],
        max_iterations: int = 10,
        llm_config: Optional[LLMConfig] = None
    ) -> AsyncGenerator[SSEEvent, None]:
        """
        Run the agent tool loop with streaming support.
        
        This is the core streaming loop that:
        1. Calls LLM with streaming
        2. Yields SSE events (content deltas, tool events, etc.)
        3. Executes tools when needed
        4. Loops until final response
        
        Args:
            initial_messages: Starting messages
            max_iterations: Max tool loops
            llm_config: LLM configuration (uses preset if not provided)
            
        Yields:
            SSEEvent objects for streaming to frontend
        """
        # Reset state for this turn
        self._new_messages = []
        self._tool_calls_info = []
        
        # Use default config if not provided
        llm_config = llm_config or LLMConfig.from_config(
            model=self.get_model(),
            stream=True
        )
        
        # Get messages for LLM (will update as we go)
        messages = initial_messages.copy()
        iteration = 0
        
        # Start overall agent interaction span (clean abstraction)
        async with self._agent_tracer.interaction(max_iterations):
            while iteration < max_iterations:
                iteration += 1
                
                # Start span for this turn (clean abstraction)
                async with self._agent_tracer.turn(iteration, len(messages)):
                    # Get tools for this agent from global registry
                    tools = tool_registry.get_openai_tools(tool_names=self.tool_names)
                    
                    # Step 1: Call LLM and stream response (yields SSE events directly)
                    content = ""
                    tool_calls = []
                    async for event in stream_llm_response(
                        messages=messages,
                        tools=tools,
                        llm_config=llm_config,
                        user_id=self.context.user_id
                    ):
                        # Extract results from llm_end event
                        if event.event == "llm_end":
                            content = event.data.get("content", "")
                            tool_calls = event.data.get("tool_calls", [])
                        
                        # Forward LLM events (content deltas, llm_end, etc.)
                        yield event
                    
                    # If no tool calls, we're done
                    if not tool_calls:
                        self._agent_tracer.record_final_turn(iteration, len(content) if content else 0)
                        assistant_msg = {"role": "assistant", "content": content or ""}
                        messages.append(assistant_msg)
                        # Track new message for saving to DB
                        self._new_messages.append(HistoryChatMessage.from_dict(assistant_msg))
                        return  # Exit generator
                    
                    # Record tool calls requested
                    self._agent_tracer.record_tool_calls_requested(tool_calls)
                    
                    # Add assistant message with tool calls
                    assistant_msg = {
                        "role": "assistant",
                        "content": content or "",
                        "tool_calls": tool_calls
                    }
                    messages.append(assistant_msg)
                    # Track new message for saving to DB
                    self._new_messages.append(HistoryChatMessage.from_dict(assistant_msg))
                    
                    # Step 2: Execute tools and get result messages
                    # Tools will emit their own status events via stream_handler
                    # Filter events to extract control flow data (pure event pattern)
                    tool_messages = []
                    async for event in self._execute_tools_step(
                        tool_calls=tool_calls,
                        context=self.context
                    ):
                        # Extract tool messages from tools_end event
                        if event.event == "tools_end":
                            tool_messages = event.data.get("tool_messages", [])
                        
                        # Forward tool events (tool_progress, tool_status, tools_end, etc.)
                        yield event
                    
                    # Add tool results to messages and track for DB
                    messages.extend(tool_messages)
                    for tool_msg in tool_messages:
                        self._new_messages.append(HistoryChatMessage.from_dict(tool_msg))
                    
                    # Show thinking indicator before next LLM call (synthesizing results)
                    yield SSEEvent(
                        event="thinking",
                        data=ThinkingEvent(message="Processing results and formulating response...").model_dump()
                    )
                    
                    # Loop continues...
    
    async def process_message_stream(
        self,
        message: str,
        chat_history: ChatHistory
    ) -> AsyncGenerator[SSEEvent, None]:
        """
        Stream chat responses with SSE events.
        
        Args:
            message: User message
            chat_history: Previous messages
        
        Yields:
            SSEEvent objects for streaming to frontend
        """
        try:
            initial_messages = self.build_messages(chat_history=chat_history)
            
            # Create LLM configuration
            llm_config = LLMConfig.from_config(stream=True)
            
            # Stream all events directly from agent loop
            async for event in self.run_tool_loop_streaming(
                initial_messages=initial_messages,
                max_iterations=10,
                llm_config=llm_config
            ):
                yield event
            
            # Done - frontend handles saving accumulated streaming content
            yield SSEEvent(
                event="done",
                data=DoneEvent().model_dump()
            )
            
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            logger.debug(f"Traceback: {traceback_module.format_exc()}")
            
            yield SSEEvent(
                event="error",
                data=ErrorEvent(error=str(e), details=traceback_module.format_exc()).model_dump()
            )
    
    def build_messages(
        self,
        chat_history: ChatHistory,
    ) -> List[Dict[str, Any]]:
        """Build messages for OpenAI API with system prompt prepended."""
        # Prepend system message and convert to OpenAI format
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(chat_history.to_openai_format())
        
        return messages

