"""
Base Agent class - reusable agent logic for main and specialized agents
"""
from typing import List, Dict, Any, Optional, AsyncGenerator, Callable
import json
import asyncio
from abc import ABC, abstractmethod

from modules.tools import tool_registry, tool_runner
from modules.resource_manager import ResourceManager
from models.sse import SSEEvent, LLMStartEvent, LLMEndEvent, ToolsEndEvent
from models.chat_history import ChatHistory, ChatMessage as HistoryChatMessage
from .llm_config import LLMConfig
from .llm_handler import LLMHandler
from .context import AgentContext
from utils.logger import get_logger
from .tracing_utils import AgentTracer

logger = get_logger(__name__)


class BaseAgent(ABC):
    """
    Base agent class with common LLM interaction logic.
    
    All agents use the global tool_registry but can specify which tools they need.
    
    Subclasses should implement:
    - get_system_prompt(): Return the system prompt for this agent
    - get_tool_names(): Return list of tool names this agent can use
    - get_model(): Return the model name to use
    """
    
    def __init__(self):
        self._history = ChatHistory()
        self._initial_messages_len = 0
        self._tool_calls_info = []  # Track tool executions for resource creation
    
    @abstractmethod
    def get_system_prompt(self, **kwargs) -> str:
        """
        Get the system prompt for this agent.
        Subclasses implement this with agent-specific prompts.
        """
        pass
    
    @abstractmethod
    def get_tool_names(self) -> Optional[List[str]]:
        """
        Get the list of tool names this agent can use.
        Return None to use all available tools.
        Return empty list [] for no tools.
        Return list of names like ['create_chart', 'analyze_data'] for specific tools.
        """
        pass
    
    @abstractmethod
    def get_model(self) -> str:
        """
        Get the model name for this agent.
        Subclasses specify their model (gpt-4, gpt-4o-mini, etc.)
        """
        pass
    
    def get_new_messages(self) -> List[HistoryChatMessage]:
        """
        Get the new messages from the last interaction (for saving to DB).
        
        Returns:
            List of ChatMessage objects added during this interaction
        """
        return self._history.get_new_messages(self._initial_messages_len)
    
    def get_tool_calls_info(self) -> List[Dict[str, Any]]:
        """Get tool call execution information from the last interaction"""
        return self._tool_calls_info
    
    async def _stream_llm_step(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        llm_config: LLMConfig,
        on_content_delta: Optional[Callable[[str], AsyncGenerator[SSEEvent, None]]],
        user_id: Optional[str] = None
    ):
        """
        Stream LLM response and accumulate content/tool_calls.
        
        Uses pure event pattern (similar to LangChain):
        - Yields SSEEvent objects throughout
        - Final event is 'llm_end' with accumulated results
        - No magic tuples, everything is strongly typed
        """
        # Emit start event
        yield SSEEvent(
            event="llm_start",
            data=LLMStartEvent(message_count=len(messages)).model_dump()
        )
        
        # Create LLM handler for this call
        llm_handler = LLMHandler(user_id=user_id)
        
        # Merge tools into LiteLLM kwargs
        llm_kwargs = llm_config.to_litellm_kwargs()
        llm_kwargs["messages"] = messages
        llm_kwargs["tools"] = tools if tools else None
        llm_kwargs["tool_choice"] = "auto" if tools else None
        llm_kwargs["stream"] = True
        if "stream_options" not in llm_kwargs:
            llm_kwargs["stream_options"] = {"include_usage": False}
        
        stream_response = await llm_handler.acompletion(**llm_kwargs)
        
        content = ""
        tool_calls = []
        reasoning_content = ""
        
        # Stream and accumulate
        async for chunk in stream_response:
            if hasattr(chunk, 'choices') and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                
                # Stream reasoning content (for o1/o3 models with extended thinking)
                if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                    reasoning_content += delta.reasoning_content
                    if on_content_delta:
                        async for event in on_content_delta(delta.reasoning_content):
                            yield event
                
                # Stream regular content deltas
                if hasattr(delta, 'content') and delta.content:
                    content += delta.content
                    if on_content_delta:
                        async for event in on_content_delta(delta.content):
                            yield event
                
                # Accumulate tool calls
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
                            if tc.function.arguments:
                                tool_calls[idx]["function"]["arguments"] += tc.function.arguments
        
        # Emit end event with accumulated results (pure event pattern)
        yield SSEEvent(
            event="llm_end",
            data=LLMEndEvent(
                content=content,
                tool_calls=tool_calls
            ).model_dump()
        )
    
    async def _execute_tools_step(
        self,
        tool_calls: List[Dict[str, Any]],
        context: AgentContext,
        on_tool_call_start: Optional[Callable[[Dict[str, Any]], AsyncGenerator[SSEEvent, None]]],
        on_tool_call_complete: Optional[Callable[[Dict[str, Any]], AsyncGenerator[SSEEvent, None]]]
    ):
        """
        Execute all tool calls in parallel and yield events.
        
        Uses pure event pattern (similar to LangChain):
        - Yields SSEEvent objects throughout
        - Final event is 'tools_end' with tool messages
        - No magic tuples, everything is strongly typed
        """
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
                stream_handler=context.stream_handler,  # Pass through stream handler
                resource_manager=context.resource_manager,
                chat_id=context.chat_id
            )
            return {
                "tool_call_id": call["id"],
                "tool_name": call["name"],
                "arguments": call["args"],
                "result": result
            }
        
        # Run all tools concurrently
        logger.info(f"{self.__class__.__name__} executing {len(parsed_calls)} tool(s) in parallel")
        results = await asyncio.gather(*[execute_single_tool(call) for call in parsed_calls])
        
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
            # Handle both dict and non-dict (e.g., string) results
            if isinstance(result, dict):
                status = "completed" if result.get("success", True) else "error"
                error_msg = result.get("message") if not result.get("success", True) else None
            else:
                # Non-dict results are considered successful
                logger.warning(f"Tool '{result_data['tool_name']}' returned non-dict result: {type(result).__name__}")
                status = "completed"
                error_msg = None
            
            self._tool_calls_info.append({
                "tool_call_id": result_data["tool_call_id"],
                "tool_name": result_data["tool_name"],
                "status": status,
                "arguments": result_data["arguments"],
                "result_data": result,
                "error": error_msg
            })
            
            # Build tool message for conversation
            tool_messages.append({
                "role": "tool",
                "tool_call_id": result_data["tool_call_id"],
                "name": result_data["tool_name"],
                "content": self._truncate_tool_result(result)
            })
        
        # Emit end event with tool messages (pure event pattern)
        yield SSEEvent(
            event="tools_end",
            data=ToolsEndEvent(tool_messages=tool_messages).model_dump()
        )
    
    async def run_tool_loop_streaming(
        self,
        initial_messages: List[Dict[str, Any]],
        context: AgentContext,  # Always required
        max_iterations: int = 10,
        llm_config: Optional[LLMConfig] = None,
        on_content_delta: Optional[Callable[[str], AsyncGenerator[SSEEvent, None]]] = None,
        on_tool_call_start: Optional[Callable[[Dict[str, Any]], AsyncGenerator[SSEEvent, None]]] = None,
        on_tool_call_complete: Optional[Callable[[Dict[str, Any]], AsyncGenerator[SSEEvent, None]]] = None,
        on_thinking: Optional[Callable[[], AsyncGenerator[SSEEvent, None]]] = None
    ) -> AsyncGenerator[SSEEvent, None]:
        """
        Run the agent tool loop with streaming support.
        
        This is the core streaming loop that:
        1. Calls LLM with streaming
        2. Yields content deltas
        3. Executes tools when needed
        4. Loops until final response
        
        Callbacks allow subclasses to customize event generation.
        
        Args:
            initial_messages: Starting messages
            user_id: User ID
            max_iterations: Max tool loops
            llm_config: LLM configuration (uses preset if not provided)
            on_content_delta: Callback for streaming text chunks
            on_tool_call_start: Callback when tool call starts
            on_tool_call_complete: Callback when tool call completes
            on_thinking: Callback for thinking indicator
            
        Yields:
            SSEEvent objects for streaming to frontend
        """
        # Use default config if not provided
        llm_config = llm_config or LLMConfig.from_config(
            model=self.get_model(),
            stream=True
        )
        
        # Build internal ChatHistory for tracking
        self._history = ChatHistory(chat_id=context.chat_id, user_id=context.user_id)
        self._history.extend_from_dicts(initial_messages)
        self._initial_messages_len = len(self._history)
        self._tool_calls_info = []  # Reset for this interaction
        
        # Get messages for LLM (will update as we go)
        messages = initial_messages.copy()
        
        iteration = 0
        
        # Create tracer for clean instrumentation
        agent_tracer = AgentTracer(
            agent_name=self.__class__.__name__,
            user_id=context.user_id,
            chat_id=context.chat_id,
            model=self.get_model()
        )
        
        # Start overall agent interaction span (clean abstraction)
        async with agent_tracer.interaction(max_iterations):
            while iteration < max_iterations:
                iteration += 1
                
                # Start span for this turn (clean abstraction)
                async with agent_tracer.turn(iteration, len(messages)):
                    # Get tools for this agent from global registry
                    tool_names = self.get_tool_names()
                    tools = tool_registry.get_openai_tools(tool_names=tool_names)
                    agent_tracer.record_tools_available(len(tools) if tools else 0)
                    
                    # Step 1: Call LLM and stream response
                    # Filter events to extract control flow data (pure event pattern)
                    content = ""
                    tool_calls = []
                    async for event in self._stream_llm_step(
                        messages=messages,
                        tools=tools,
                        llm_config=llm_config,
                        on_content_delta=on_content_delta,
                        user_id=context.user_id
                    ):
                        # Check if it's the llm_end event (contains results)
                        if event.event == "llm_end":
                            content = event.data.get("content", "")
                            tool_calls = event.data.get("tool_calls", [])
                        
                        # Always forward the event to frontend
                        yield event
                    
                    # If no tool calls, we're done
                    if not tool_calls:
                        agent_tracer.record_final_turn(iteration, len(content) if content else 0)
                        assistant_msg = {"role": "assistant", "content": content or ""}
                        messages.append(assistant_msg)
                        self._history.add_message(HistoryChatMessage.from_dict(assistant_msg))
                        return  # Exit generator
                    
                    # Record tool calls requested
                    agent_tracer.record_tool_calls_requested(tool_calls)
                    
                    # Add assistant message with tool calls
                    assistant_msg = {
                        "role": "assistant",
                        "content": content or "",
                        "tool_calls": tool_calls
                    }
                    messages.append(assistant_msg)
                    self._history.add_message(HistoryChatMessage.from_dict(assistant_msg))
                    
                    # Step 2: Execute tools and get result messages
                    # Filter events to extract control flow data (pure event pattern)
                    tool_messages = []
                    async for event in self._execute_tools_step(
                        tool_calls=tool_calls,
                        context=context,
                        on_tool_call_start=on_tool_call_start,
                        on_tool_call_complete=on_tool_call_complete
                    ):
                        # Check if it's the tools_end event (contains tool messages)
                        if event.event == "tools_end":
                            tool_messages = event.data.get("tool_messages", [])
                        
                        # Always forward the event to frontend
                        yield event
                    
                    # Add tool results to messages and history
                    messages.extend(tool_messages)
                    for tool_msg in tool_messages:
                        self._history.add_message(HistoryChatMessage.from_dict(tool_msg))
                    
                    # Show thinking before next iteration
                    if on_thinking:
                        async for event in on_thinking():
                            yield event
                    
                    # Loop continues...
    
    def build_messages(
        self,
        user_message: str,
        chat_history: ChatHistory,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Build messages for LLM API.
        
        Note: System messages are NOT stored in DB (they're ephemeral and fixed), so we 
        always prepend a fresh one. The chat_history from DB contains user/assistant/tool
        messages only. The current user_message is already in chat_history (added by
        chat_service before calling the agent).
        
        Args:
            user_message: Current user message (for reference/logging only)
            chat_history: Complete conversation history from DB (includes current user message)
            **kwargs: Additional args for system prompt (unused now - system prompt is fixed)
            
        Returns:
            List of messages in OpenAI format with fixed system prompt prepended
        """
        system_prompt = self.get_system_prompt()
        
        # Build using ChatHistory model for type safety
        messages = ChatHistory()
        
        # Always add system message (fixed, not stored in DB)
        messages.add_system_message(system_prompt)
        
        # Add complete chat history from DB (already includes current user message)
        messages.messages.extend(chat_history.messages)
        
        return messages.to_openai_format()
    
    def _truncate_tool_result(self, result: Any, max_size: int = 50000) -> str:
        """
        Truncate large tool results to avoid overwhelming the LLM.
        
        Args:
            result: Tool result (can be dict, string, or other type)
            max_size: Max size in bytes
            
        Returns:
            JSON string (potentially truncated)
        """
        # Handle non-dict results (e.g., strings)
        if not isinstance(result, dict):
            logger.debug(f"Truncating non-dict result of type {type(result).__name__}")
            try:
                result_str = json.dumps(result) if not isinstance(result, str) else result
            except Exception as e:
                logger.error(f"Error serializing tool result: {e}")
                return json.dumps({
                    "success": False,
                    "error": f"Failed to serialize: {str(e)}"
                })
        else:
            # Handle dict results
            try:
                result_str = json.dumps(result)
            except Exception as e:
                logger.error(f"Error serializing tool result: {e}")
                return json.dumps({
                    "success": False,
                    "error": f"Failed to serialize: {str(e)}"
                })
        
        if len(result_str) > max_size:
            logger.warning(f"Tool result too large ({len(result_str)} bytes), truncating")
            
            # Intelligent truncation for arrays (only for dict results)
            if isinstance(result, dict) and "data" in result and isinstance(result["data"], list):
                original_count = len(result["data"])
                result["data"] = result["data"][:20]  # Keep first 20 items
                result["_truncated"] = f"Showing 20 of {original_count} items"
                result_str = json.dumps(result)
            
            # Hard truncate if still too large
            if len(result_str) > max_size:
                result_str = result_str[:max_size] + '... [TRUNCATED]"}'
        
        return result_str

