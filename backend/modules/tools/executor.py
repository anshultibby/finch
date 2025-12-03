"""
Tool Executor - Standalone tool execution with configurable policies

This module provides a standalone tool executor that can:
- Execute a list of tools in parallel or series
- Apply truncation policies to results
- Handle streaming events from tools (SSE events yielded by tools)
- Return structured execution results

Decouples tool execution from agent logic for better reusability.
"""
from typing import List, Dict, Any, Optional, Callable, AsyncGenerator
from enum import Enum
import asyncio
import json
import inspect
from datetime import datetime
from pydantic import BaseModel, Field

from .runner import tool_runner
from modules.agent.context import AgentContext
from models.sse import SSEEvent, ToolsEndEvent
from utils.logger import get_logger

logger = get_logger(__name__)


class TruncationPolicy(BaseModel):
    """Policy for truncating tool results before sending to LLM"""
    max_chars: int = Field(default=10000, description="Maximum characters to keep")
    
    class Config:
        arbitrary_types_allowed = True


class ExecutionMode(str, Enum):
    """Tool execution mode"""
    PARALLEL = "parallel"  # Execute all tools concurrently
    SEQUENTIAL = "sequential"  # Execute tools one by one


class ToolCallRequest(BaseModel):
    """Request for executing a single tool"""
    id: str = Field(description="Unique tool call ID")
    name: str = Field(description="Tool name")
    arguments: Dict[str, Any] = Field(description="Tool arguments")


class ToolExecutionResult(BaseModel):
    """Result of a single tool execution"""
    tool_call_id: str
    tool_name: str
    arguments: Dict[str, Any]
    raw_result: Dict[str, Any] = Field(description="Untruncated result")
    truncated_result: str = Field(description="Result truncated for LLM")
    success: bool
    error: Optional[str] = None
    duration_ms: float
    was_truncated: bool
    
    class Config:
        arbitrary_types_allowed = True


class ToolExecutionBatch(BaseModel):
    """Results from executing a batch of tools"""
    results: List[ToolExecutionResult]
    tool_messages: List[Dict[str, Any]] = Field(
        description="OpenAI-format tool messages for conversation"
    )
    total_duration_ms: float
    execution_mode: ExecutionMode
    
    def get_result_by_id(self, tool_call_id: str) -> Optional[ToolExecutionResult]:
        """Get a specific result by tool call ID"""
        return next((r for r in self.results if r.tool_call_id == tool_call_id), None)
    
    def all_succeeded(self) -> bool:
        """Check if all tools succeeded"""
        return all(r.success for r in self.results)
    
    def get_failed_tools(self) -> List[ToolExecutionResult]:
        """Get all failed tool results"""
        return [r for r in self.results if not r.success]


class ToolExecutor:
    """
    Standalone tool executor with configurable policies.
    
    Responsibilities:
    - Execute tools with specified mode (parallel/sequential)
    - Apply truncation policies to results
    - Handle streaming events
    - Return structured results
    
    Usage:
        executor = ToolExecutor(
            truncation_policy=TruncationPolicy(strategy=TruncationStrategy.SMART),
            execution_mode=ExecutionMode.PARALLEL
        )
        
        results = await executor.execute_batch(
            tool_calls=[...],
            context=context,
            on_tool_start=callback,
            on_tool_complete=callback
        )
    """
    
    def __init__(
        self,
        truncation_policy: Optional[TruncationPolicy] = None,
        execution_mode: ExecutionMode = ExecutionMode.PARALLEL,
        runner=None
    ):
        """
        Initialize tool executor
        
        Args:
            truncation_policy: Policy for truncating results (defaults to SMART)
            execution_mode: How to execute tools (parallel or sequential)
            runner: ToolRunner instance (defaults to global runner)
        """
        self.truncation_policy = truncation_policy or TruncationPolicy()
        self.execution_mode = execution_mode
        self.runner = runner or tool_runner
    
    async def execute_batch(
        self,
        tool_calls: List[ToolCallRequest],
        context: AgentContext,
        on_tool_start: Optional[Callable[[Dict[str, Any]], AsyncGenerator[SSEEvent, None]]] = None,
        on_tool_complete: Optional[Callable[[Dict[str, Any]], AsyncGenerator[SSEEvent, None]]] = None
    ) -> ToolExecutionBatch:
        """
        Execute a batch of tool calls
        
        Args:
            tool_calls: List of tool call requests
            context: Agent execution context
            on_tool_start: Optional callback when tool starts (yields SSE events)
            on_tool_complete: Optional callback when tool completes (yields SSE events)
        
        Returns:
            ToolExecutionBatch with all results and tool messages
        """
        start_time = asyncio.get_event_loop().time()
        
        # Emit start events
        if on_tool_start:
            for call in tool_calls:
                async for event in on_tool_start({
                    "tool_call_id": call.id,
                    "tool_name": call.name,
                    "arguments": call.arguments
                }):
                    # Events are yielded but not stored (caller handles streaming)
                    pass
        
        # Execute based on mode
        if self.execution_mode == ExecutionMode.PARALLEL:
            results = await self._execute_parallel(tool_calls, context)
        else:
            results = await self._execute_sequential(tool_calls, context)
        
        # Emit complete events
        if on_tool_complete:
            for result in results:
                async for event in on_tool_complete({
                    "tool_call_id": result.tool_call_id,
                    "tool_name": result.tool_name,
                    "result": result.raw_result
                }):
                    pass
        
        # Build tool messages for OpenAI conversation format
        tool_messages = []
        for result in results:
            tool_messages.append({
                "role": "tool",
                "tool_call_id": result.tool_call_id,
                "name": result.tool_name,
                "content": result.truncated_result
            })
        
        end_time = asyncio.get_event_loop().time()
        total_duration = (end_time - start_time) * 1000
        
        return ToolExecutionBatch(
            results=results,
            tool_messages=tool_messages,
            total_duration_ms=total_duration,
            execution_mode=self.execution_mode
        )
    
    async def _execute_parallel(
        self,
        tool_calls: List[ToolCallRequest],
        context: AgentContext
    ) -> List[ToolExecutionResult]:
        """Execute all tools in parallel"""
        logger.info(f"Executing {len(tool_calls)} tool(s) in parallel")
        
        async def execute_single(call: ToolCallRequest) -> ToolExecutionResult:
            return await self._execute_single_tool(call, context)
        
        return await asyncio.gather(*[execute_single(call) for call in tool_calls])
    
    async def _execute_sequential(
        self,
        tool_calls: List[ToolCallRequest],
        context: AgentContext
    ) -> List[ToolExecutionResult]:
        """Execute tools one by one"""
        logger.info(f"Executing {len(tool_calls)} tool(s) sequentially")
        
        results = []
        for call in tool_calls:
            result = await self._execute_single_tool(call, context)
            results.append(result)
        
        return results
    
    async def _execute_single_tool(
        self,
        call: ToolCallRequest,
        context: AgentContext
    ) -> ToolExecutionResult:
        """Execute a single tool and return structured result (events are ignored here)"""
        start_time = asyncio.get_event_loop().time()
        
        # Execute tool - runner now returns an async generator
        # Iterate through it to get events (ignored in non-streaming batch) and final result
        raw_result = None
        async for item in self.runner.execute(
            tool_name=call.name,
            arguments=call.arguments,
            context=context
        ):
            if isinstance(item, SSEEvent):
                # In non-streaming batch mode, we ignore events
                # (execute_batch_streaming handles events properly)
                pass
            else:
                # Last non-SSEEvent item is the final result
                # Make sure it's not an async generator
                if inspect.isasyncgen(item):
                    logger.error(f"Tool {call.name} yielded an async generator instead of a result!")
                    raw_result = {
                        "success": False,
                        "error": "Tool returned async generator instead of result",
                        "message": f"Tool {call.name} implementation error"
                    }
                else:
                    raw_result = item
        
        # Ensure we got a result
        if raw_result is None:
            raw_result = {
                "success": False,
                "error": "Tool did not return a result",
                "message": f"Tool {call.name} completed but did not yield a final result"
            }
        
        # Convert ToolResponse to LLM content using tool's own formatting
        if hasattr(raw_result, 'to_llm_content'):
            llm_content = raw_result.to_llm_content()
        else:
            # Fallback for dict results (legacy)
            llm_content = json.dumps(raw_result) if isinstance(raw_result, dict) else str(raw_result)
        
        # Apply safety truncation only if needed
        truncated, was_truncated = self._apply_truncation(llm_content)
        
        # Extract success/error from ToolResponse
        if hasattr(raw_result, 'success'):
            success = raw_result.success
            error = raw_result.error if hasattr(raw_result, 'error') else None
        else:
            # Fallback for dict results (legacy)
            success = raw_result.get("success", True) if isinstance(raw_result, dict) else True
            error = raw_result.get("error") if isinstance(raw_result, dict) and not success else None
        
        end_time = asyncio.get_event_loop().time()
        duration = (end_time - start_time) * 1000
        
        return ToolExecutionResult(
            tool_call_id=call.id,
            tool_name=call.name,
            arguments=call.arguments,
            raw_result=raw_result,
            truncated_result=truncated,  # Safety truncation only
            success=success,
            error=error,
            duration_ms=duration,
            was_truncated=was_truncated
        )
    
    def _build_execution_result(
        self,
        call: ToolCallRequest,
        raw_result: Dict[str, Any],
        duration_ms: float
    ) -> ToolExecutionResult:
        """Build ToolExecutionResult from raw result dict"""
        # Ensure we have a valid result
        if raw_result is None:
            raw_result = {
                "success": False,
                "error": "Tool did not return a result",
                "message": f"Tool {call.name} completed but did not yield a final result"
            }
        
        # Convert ToolResponse to LLM content
        if hasattr(raw_result, 'to_llm_content'):
            llm_content = raw_result.to_llm_content()
        else:
            # Fallback for dict results (legacy)
            llm_content = json.dumps(raw_result) if isinstance(raw_result, dict) else str(raw_result)
        
        # Apply safety truncation
        truncated, was_truncated = self._apply_truncation(llm_content)
        
        # Extract success/error
        if hasattr(raw_result, 'success'):
            success = raw_result.success
            error = raw_result.error if hasattr(raw_result, 'error') else None
        else:
            # Fallback for dict results (legacy)
            success = raw_result.get("success", True) if isinstance(raw_result, dict) else True
            error = raw_result.get("error") if isinstance(raw_result, dict) and not success else None
        
        return ToolExecutionResult(
            tool_call_id=call.id,
            tool_name=call.name,
            arguments=call.arguments,
            raw_result=raw_result,
            truncated_result=truncated,
            success=success,
            error=error,
            duration_ms=duration_ms,
            was_truncated=was_truncated
        )
    
    def _apply_truncation(self, content: str) -> tuple[str, bool]:
        """
        Apply safety truncation to content string.
        
        This is a SAFETY mechanism - tools should manage their own output size.
        
        Args:
            content: String content (already formatted by tool)
        
        Returns:
            Tuple of (truncated_string, was_truncated)
        """
        policy = self.truncation_policy
        
        # Check if truncation needed
        if len(content) <= policy.max_chars:
            return content, False
        
        logger.warning(
            f"Content exceeded {policy.max_chars} chars ({len(content)} chars). "
            "Tool should handle its own output size. Applying safety truncation."
        )
        
        # Safety truncation
        truncated = content[:policy.max_chars] + "... [TRUNCATED BY EXECUTOR]"
        return truncated, True
    
    def _enrich_event_with_metadata(
        self, 
        event: SSEEvent, 
        tool_call_id: str, 
        tool_name: str
    ) -> SSEEvent:
        """
        Enrich SSE events with tool metadata for frontend display.
        
        Tools emit generic events (tool_status, tool_progress, tool_log) without knowing
        their call ID. This method adds the metadata so the frontend can associate events
        with specific tool calls.
        
        Args:
            event: Original SSE event from tool
            tool_call_id: Unique ID for this tool call
            tool_name: Name of the tool being executed
        
        Returns:
            Enriched SSEEvent with tool_call_id and tool_name in data
        """
        # Events that should be enriched with tool metadata
        events_to_enrich = {"tool_status", "tool_progress", "tool_log"}
        
        if event.event in events_to_enrich:
            # Create a copy of the event data and add metadata
            enriched_data = event.data.copy()
            
            # Add tool metadata if not already present
            if "tool_call_id" not in enriched_data:
                enriched_data["tool_call_id"] = tool_call_id
            if "tool_name" not in enriched_data:
                enriched_data["tool_name"] = tool_name
            
            # Return new event with enriched data
            return SSEEvent(event=event.event, data=enriched_data)
        
        # Return original event for non-tool events
        return event
    
    async def execute_batch_streaming(
        self,
        tool_calls: List[ToolCallRequest],
        context: AgentContext,
        enable_tool_streaming: bool = True
    ) -> AsyncGenerator[SSEEvent, None]:
        """
        Execute batch with streaming support - simple SSE design with real-time parallel streaming.
        
        Yields SSE events throughout execution:
        1. tool_call_start events for each tool
        2. Real-time SSE events from tools (tool_status, tool_log, tool_progress, etc.)
        3. tool_call_complete events for each tool
        4. Final tools_end event with tool messages and results
        
        In parallel mode, events from all tools stream in real-time as they're generated.
        
        Args:
            tool_calls: List of tools to execute
            context: Agent execution context
            enable_tool_streaming: Whether to stream tool-emitted events (default: True)
        
        Yields:
            SSEEvent objects throughout execution
        """
        logger.info(f"🌊 Executing {len(tool_calls)} tool(s) with streaming {'ENABLED' if enable_tool_streaming else 'DISABLED'}")
        
        # Emit tool_call_start events for all tools
        for call in tool_calls:
            yield SSEEvent(
                event="tool_call_start",
                data={
                    "tool_call_id": call.id,
                    "tool_name": call.name,
                    "arguments": call.arguments
                }
            )
        
        # Execute tools and collect results
        results = []
        event_count = 0
        
        if self.execution_mode == ExecutionMode.PARALLEL:
            # Parallel execution with REAL-TIME event streaming using event queue
            logger.info(f"📡 Using event queue for real-time parallel streaming")
            
            # Create event queue for real-time streaming
            event_queue = asyncio.Queue()
            
            async def execute_and_stream(call: ToolCallRequest):
                """Execute tool and stream events to queue in real-time"""
                start_time = asyncio.get_event_loop().time()
                final_result = None
                
                try:
                    async for item in self.runner.execute(
                        tool_name=call.name,
                        arguments=call.arguments,
                        context=context
                    ):
                        if isinstance(item, SSEEvent):
                            # Enrich event with tool metadata for frontend
                            enriched_event = self._enrich_event_with_metadata(item, call.id, call.name)
                            # Stream enriched event to queue immediately
                            await event_queue.put(("event", enriched_event))
                        else:
                            # Make sure it's not an async generator
                            if inspect.isasyncgen(item):
                                logger.error(f"Tool {call.name} yielded an async generator instead of a result!")
                                final_result = {
                                    "success": False,
                                    "error": "Tool returned async generator instead of result",
                                    "message": f"Tool {call.name} implementation error"
                                }
                            else:
                                final_result = item
                    
                    # Ensure we got a result
                    if final_result is None:
                        final_result = {
                            "success": False,
                            "error": "Tool did not return a result",
                            "message": f"Tool {call.name} completed but did not yield a final result"
                        }
                    
                    end_time = asyncio.get_event_loop().time()
                    duration = (end_time - start_time) * 1000
                    
                    # Signal completion with result
                    await event_queue.put(("result", call, final_result, duration))
                    
                except Exception as e:
                    logger.error(f"Error in tool {call.name}: {str(e)}")
                    # Put error result in queue
                    await event_queue.put(("result", call, {
                        "success": False,
                        "error": str(e),
                        "message": f"Tool execution failed: {str(e)}"
                    }, 0.0))
            
            # Start all tools concurrently
            tasks = [asyncio.create_task(execute_and_stream(call)) for call in tool_calls]
            
            # Stream events from queue as they arrive
            completed_count = 0
            while completed_count < len(tool_calls):
                item = await event_queue.get()
                
                if item[0] == "event":
                    # Real-time SSE event from a tool
                    if enable_tool_streaming:
                        event_count += 1
                        yield item[1]
                
                elif item[0] == "result":
                    # Tool completed - build result
                    call, final_result, duration = item[1], item[2], item[3]
                    results.append(self._build_execution_result(call, final_result, duration))
                    completed_count += 1
            
            # Wait for all tasks to complete (should already be done)
            await asyncio.gather(*tasks, return_exceptions=True)
            
        else:
            # Sequential - stream events as they come
            for call in tool_calls:
                start_time = asyncio.get_event_loop().time()
                final_result = None
                
                async for item in self.runner.execute(
                    tool_name=call.name,
                    arguments=call.arguments,
                    context=context
                ):
                    if isinstance(item, SSEEvent):
                        if enable_tool_streaming:
                            event_count += 1
                            # Enrich event with tool metadata for frontend
                            enriched_event = self._enrich_event_with_metadata(item, call.id, call.name)
                            yield enriched_event
                    else:
                        # Make sure it's not an async generator
                        if inspect.isasyncgen(item):
                            logger.error(f"Tool {call.name} yielded an async generator instead of a result!")
                            final_result = {
                                "success": False,
                                "error": "Tool returned async generator instead of result",
                                "message": f"Tool {call.name} implementation error"
                            }
                        else:
                            final_result = item
                
                end_time = asyncio.get_event_loop().time()
                duration = (end_time - start_time) * 1000
                
                # Build ToolExecutionResult
                results.append(self._build_execution_result(call, final_result, duration))
        
        logger.info(f"🌊 Tool execution complete: {event_count} SSE events streamed")
        
        # Emit tool_call_complete events for all tools
        for result in results:
            # Get a brief summary of the result to show the user
            result_summary = None
            if result.success:
                # Show first 500 chars of the truncated result as a preview
                result_summary = result.truncated_result[:500] if len(result.truncated_result) > 500 else result.truncated_result
            
            yield SSEEvent(
                event="tool_call_complete",
                data={
                    "tool_call_id": result.tool_call_id,
                    "tool_name": result.tool_name,
                    "status": "completed" if result.success else "error",
                    "error": result.error,
                    "result_summary": result_summary
                }
            )
        
        # Build tool messages for conversation
        tool_messages = []
        # Build execution results for tracking
        execution_results = []
        
        for result in results:
            tool_messages.append({
                "role": "tool",
                "tool_call_id": result.tool_call_id,
                "name": result.tool_name,
                "content": result.truncated_result
            })
            
            execution_results.append({
                "tool_call_id": result.tool_call_id,
                "tool_name": result.tool_name,
                "status": "completed" if result.success else "error",
                "arguments": result.arguments,
                "result_data": result.raw_result,
                "error": result.error,
                "duration_ms": result.duration_ms,
                "was_truncated": result.was_truncated
            })
        
        # Yield final tools_end event with BOTH tool messages AND detailed results
        yield SSEEvent(
            event="tools_end",
            data=ToolsEndEvent(
                tool_messages=tool_messages,
                execution_results=execution_results
            ).model_dump()
        )


# Factory functions for common configurations

def create_default_executor() -> ToolExecutor:
    """Create executor with default 10K char truncation"""
    return ToolExecutor(
        truncation_policy=TruncationPolicy(max_chars=10000),
        execution_mode=ExecutionMode.PARALLEL
    )


def create_sequential_executor(max_chars: int = 10000) -> ToolExecutor:
    """Create executor that runs tools sequentially"""
    return ToolExecutor(
        truncation_policy=TruncationPolicy(max_chars=max_chars),
        execution_mode=ExecutionMode.SEQUENTIAL
    )

