"""
Base Agent class - reusable agent logic for main and specialized agents
"""
from typing import List, Dict, Any, Optional, AsyncGenerator, Callable
import json
import asyncio
from datetime import datetime
from abc import ABC, abstractmethod

from modules.tools import tool_registry, tool_runner, ToolContext
from modules.resource_manager import ResourceManager
from models.sse import SSEEvent
from .llm_config import LLMConfig
from .llm_handler import LLMHandler
from .context import AgentContext


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
        self._last_messages = []
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
    
    def get_new_messages(self) -> List[Dict[str, Any]]:
        """Get the new messages from the last interaction (for saving to DB)"""
        return self._last_messages[self._initial_messages_len:]
    
    def get_tool_calls_info(self) -> List[Dict[str, Any]]:
        """Get tool call execution information from the last interaction"""
        return self._tool_calls_info
    
    async def _stream_llm_step(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        llm_config: LLMConfig,
        on_content_delta: Optional[Callable[[str], AsyncGenerator[SSEEvent, None]]],
        session_id: Optional[str] = None
    ):
        """
        One iteration: Call LLM with streaming and accumulate response
        
        Yields SSE events, then yields final (content, tool_calls) tuple
        """
        # Create LLM handler for this call
        llm_handler = LLMHandler(session_id=session_id)
        
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
        
        # Stream and accumulate
        async for chunk in stream_response:
            if hasattr(chunk, 'choices') and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                
                # Stream content deltas
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
        
        # Yield final result (special marker)
        yield ("__result__", content, tool_calls)
    
    async def _execute_tools_step(
        self,
        tool_calls: List[Dict[str, Any]],
        context: AgentContext,
        on_tool_call_start: Optional[Callable[[Dict[str, Any]], AsyncGenerator[SSEEvent, None]]],
        on_tool_call_complete: Optional[Callable[[Dict[str, Any]], AsyncGenerator[SSEEvent, None]]]
    ):
        """
        One iteration: Execute all tool calls in parallel and yield events
        
        Yields SSE events, then yields final tool_messages list
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
                session_id=context.session_id,
                user_id=context.user_id,
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
        print(f"🔧 Executing {len(parsed_calls)} tool(s) in parallel", flush=True)
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
            session_id: User session
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
        
        messages = initial_messages.copy()
        self._last_messages = messages
        self._initial_messages_len = len(initial_messages)
        self._tool_calls_info = []  # Reset for this interaction
        
        iteration = 0
        
        try:
            while iteration < max_iterations:
                iteration += 1
                
                # Get tools for this agent from global registry
                tool_names = self.get_tool_names()
                tools = tool_registry.get_openai_tools(tool_names=tool_names)
                
                # Step 1: Call LLM and stream response
                content = ""
                tool_calls = []
                async for event in self._stream_llm_step(
                    messages=messages,
                    tools=tools,
                    llm_config=llm_config,
                    on_content_delta=on_content_delta,
                    session_id=context.session_id
                ):
                    # Check if it's the result marker or SSE event
                    if isinstance(event, tuple) and event[0] == "__result__":
                        _, content, tool_calls = event
                    else:
                        # Forward SSE event
                        yield event
                
                # If no tool calls, we're done
                if not tool_calls:
                    messages.append({"role": "assistant", "content": content or ""})
                    return  # Exit generator
                
                # Add assistant message with tool calls
                messages.append({
                    "role": "assistant",
                    "content": content or "",
                    "tool_calls": tool_calls
                })
                
                # Step 2: Execute tools and get result messages
                tool_messages = []
                async for event in self._execute_tools_step(
                    tool_calls=tool_calls,
                    context=context,
                    on_tool_call_start=on_tool_call_start,
                    on_tool_call_complete=on_tool_call_complete
                ):
                    # Check if it's the result marker or SSE event
                    if isinstance(event, tuple) and event[0] == "__tool_messages__":
                        _, tool_messages = event
                    else:
                        # Forward SSE event
                        yield event
                
                # Add tool results to messages
                messages.extend(tool_messages)
                
                # Show thinking before next iteration
                if on_thinking:
                    async for event in on_thinking():
                        yield event
                
                # Loop continues...
        
        except Exception as e:
            print(f"❌ {self.__class__.__name__} streaming error: {str(e)}", flush=True)
            raise
    
    async def run_tool_loop(
        self,
        initial_messages: List[Dict[str, Any]],
        context: AgentContext,  # Always required
        max_iterations: int = 10,
        llm_config: Optional[LLMConfig] = None
    ) -> Dict[str, Any]:
        """
        Run the agent tool loop (non-streaming).
        
        Returns:
            {
                "content": str,
                "tool_results": List[Dict],
                "final_response": str,
                "iterations": int
            }
        """
        # Use default config if not provided
        llm_config = llm_config or LLMConfig.from_config(
            model=self.get_model(),
            stream=False
        )
        
        messages = initial_messages.copy()
        self._last_messages = messages
        self._initial_messages_len = len(initial_messages)
        
        tool_results = []
        iteration = 0
        
        try:
            while iteration < max_iterations:
                iteration += 1
                
                # Get tools for this agent from global registry
                tool_names = self.get_tool_names()
                tools = tool_registry.get_openai_tools(tool_names=tool_names)
                
                # Create LLM handler for this call
                llm_handler = LLMHandler(session_id=context.session_id)
                
                # Prepare LiteLLM kwargs
                llm_kwargs = llm_config.to_litellm_kwargs()
                llm_kwargs["messages"] = messages
                llm_kwargs["tools"] = tools if tools else None
                llm_kwargs["tool_choice"] = "auto" if tools else None
                
                # Call LLM (non-streaming)
                response = await llm_handler.acompletion(**llm_kwargs)
                
                response_message = response.choices[0].message
                content = response_message.content or ""
                
                # Check for tool calls
                if hasattr(response_message, 'tool_calls') and response_message.tool_calls:
                    # Add assistant message with tool calls
                    tool_calls_list = []
                    for tc in response_message.tool_calls:
                        tool_calls_list.append({
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        })
                    
                    messages.append({
                        "role": "assistant",
                        "content": content,
                        "tool_calls": tool_calls_list
                    })
                    
                    # Execute all tools in parallel
                    async def execute_tool_with_metadata(tc):
                        func_name = tc.function.name
                        func_args = json.loads(tc.function.arguments)
                        
                        result = await tool_runner.execute(
                            tool_name=func_name,
                            arguments=func_args,
                            session_id=context.session_id,
                            user_id=context.user_id,
                            resource_manager=context.resource_manager,
                            chat_id=context.chat_id
                        )
                        
                        return {
                            "tool_call_id": tc.id,
                            "tool_name": func_name,
                            "arguments": func_args,
                            "result": result
                        }
                    
                    print(f"🔧 {self.__class__.__name__} executing {len(response_message.tool_calls)} tool(s) in parallel", flush=True)
                    
                    # Run all tools concurrently
                    execution_results = await asyncio.gather(
                        *[execute_tool_with_metadata(tc) for tc in response_message.tool_calls]
                    )
                    
                    # Process results
                    for exec_result in execution_results:
                        tool_results.append({
                            "tool_name": exec_result["tool_name"],
                            "arguments": exec_result["arguments"],
                            "result": exec_result["result"]
                        })
                        
                        # Add tool result to messages
                        messages.append({
                            "role": "tool",
                            "tool_call_id": exec_result["tool_call_id"],
                            "name": exec_result["tool_name"],
                            "content": self._truncate_tool_result(exec_result["result"])
                        })
                    
                    # Continue loop (LLM will process tool results)
                    continue
                else:
                    # No tool calls - final response
                    messages.append({
                        "role": "assistant",
                        "content": content
                    })
                    
                    return {
                        "success": True,
                        "content": content,
                        "tool_results": tool_results,
                        "final_response": content,
                        "iterations": iteration
                    }
            
            # Max iterations reached
            return {
                "success": False,
                "message": f"Max iterations ({max_iterations}) reached without final response",
                "tool_results": tool_results,
                "iterations": iteration
            }
        
        except Exception as e:
            print(f"❌ {self.__class__.__name__} error: {str(e)}", flush=True)
            return {
                "success": False,
                "message": f"Agent error: {str(e)}",
                "tool_results": tool_results,
                "iterations": iteration
            }
    
    def build_messages(
        self,
        user_message: str,
        chat_history: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Build messages for LLM API.
        
        Args:
            user_message: Current user message
            chat_history: Previous conversation history
            **kwargs: Additional args for system prompt
            
        Returns:
            List of messages in OpenAI format
        """
        # Get base system prompt
        system_prompt = self.get_system_prompt(**kwargs)
        
        # Add resource information if provided via kwargs
        if 'resource_manager' in kwargs and kwargs['resource_manager']:
            resource_section = kwargs['resource_manager'].to_system_prompt_section()
            if resource_section:
                system_prompt += "\n\n" + resource_section
        
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        if chat_history:
            for msg in chat_history:
                if msg["role"] in ["user", "assistant", "tool"]:
                    messages.append(msg)
        
        messages.append({"role": "user", "content": user_message})
        
        return messages
    
    def _truncate_tool_result(self, result: Dict[str, Any], max_size: int = 50000) -> str:
        """
        Truncate large tool results to avoid overwhelming the LLM.
        
        Args:
            result: Tool result dictionary
            max_size: Max size in bytes
            
        Returns:
            JSON string (potentially truncated)
        """
        try:
            result_str = json.dumps(result)
        except Exception as e:
            print(f"❌ Error serializing tool result: {e}", flush=True)
            return json.dumps({
                "success": False,
                "error": f"Failed to serialize: {str(e)}"
            })
        
        if len(result_str) > max_size:
            print(f"⚠️ Tool result too large ({len(result_str)} bytes), truncating", flush=True)
            
            # Intelligent truncation for arrays
            if "data" in result and isinstance(result["data"], list):
                original_count = len(result["data"])
                result["data"] = result["data"][:20]  # Keep first 20 items
                result["_truncated"] = f"Showing 20 of {original_count} items"
                result_str = json.dumps(result)
            
            # Hard truncate if still too large
            if len(result_str) > max_size:
                result_str = result_str[:max_size] + '... [TRUNCATED]"}'
        
        return result_str

