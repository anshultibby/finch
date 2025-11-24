# ToolExecutor - Clean Event-Driven Design

## Overview

The `ToolExecutor` provides a standalone, event-driven tool execution system inspired by LangChain's event pattern. **Everything is an event** - no magic tuples, no special return values, just SSEEvent objects flowing through async generators.

## Core Principles

1. **Pure Event Pattern**: All communication happens via `SSEEvent` objects
2. **Single Execution**: One call to `execute_batch_streaming()` handles everything
3. **Configurable Truncation**: Simple, policy-based result truncation
4. **Real-time Streaming**: Tool events are streamed as they occur
5. **Clean Separation**: Execution logic is decoupled from agent orchestration

## Architecture

```
┌─────────────┐
│   Agent     │
│  (BaseAgent)│
└──────┬──────┘
       │
       │ async for event in executor.execute_batch_streaming(...)
       │
       ↓
┌─────────────────────────────────────────────────────┐
│              ToolExecutor                            │
│                                                      │
│  1. Parse tool calls                                 │
│  2. Emit start events → [SSEEvent]                   │
│  3. Execute tools in parallel/sequential             │
│     ├─ Create stream handlers (optional)             │
│     ├─ Queue tool events in real-time               │
│     └─ Apply truncation policy                      │
│  4. Emit complete events → [SSEEvent]                │
│  5. Emit tools_end event → [SSEEvent]                │
│     └─ Contains: tool_messages + execution_results   │
└─────────────────────────────────────────────────────┘
```

## Event Flow

```
┌──────────────────┐
│ tool_call_start  │  ← Emitted for each tool (via callback)
└──────────────────┘
        ↓
┌──────────────────┐
│   tool_options   │  ← Tool-emitted events (present_options, etc.)
│   tool_progress  │  ← Streamed in real-time via ToolStreamHandler
│   tool_status    │
│   tool_log       │
└──────────────────┘
        ↓
┌──────────────────┐
│tool_call_complete│  ← Emitted for each tool (via callback)
└──────────────────┘
        ↓
┌──────────────────┐
│   tools_end      │  ← Final event with results
│                  │
│   data: {        │
│     tool_messages: [...],      # For LLM conversation
│     execution_results: [...]   # For tracking/logging
│   }              │
└──────────────────┘
```

## Usage

### Basic Usage (BaseAgent)

```python
class MyAgent(BaseAgent):
    async def _execute_tools_step(self, tool_calls, context, on_tool_call_start, on_tool_call_complete):
        """Execute tools with clean event streaming"""
        
        # Parse tool calls
        requests = [
            ToolCallRequest(id=tc["id"], name=tc["function"]["name"], arguments=tc["function"]["arguments"])
            for tc in tool_calls
        ]
        
        # Stream all events
        async for event in self._tool_executor.execute_batch_streaming(
            tool_calls=requests,
            context=context,
            on_tool_start=on_tool_call_start,
            on_tool_complete=on_tool_call_complete,
            stream_handler_factory=None  # No tool streaming
        ):
            # Extract tracking info from tools_end
            if event.event == "tools_end":
                self._tool_calls_info.extend(event.data.get("execution_results", []))
            
            # Forward event (pure event pattern!)
            yield event
```

### Advanced Usage (ChatAgent with Tool Streaming)

```python
class ChatAgent(BaseAgent):
    async def _execute_tools_step(self, tool_calls, context, on_tool_call_start, on_tool_call_complete):
        """Execute tools with real-time tool event streaming"""
        
        # Define stream handler factory for tool events
        def create_stream_handler(tool_call_id: str, tool_name: str) -> ToolStreamHandler:
            return ToolStreamHandler(
                callback=None,  # ToolExecutor creates the callback
                tool_call_id=tool_call_id,
                tool_name=tool_name
            )
        
        # Parse tool calls
        requests = [...]
        
        # Stream all events (including tool-emitted events)
        async for event in self._tool_executor.execute_batch_streaming(
            tool_calls=requests,
            context=context,
            on_tool_start=on_tool_call_start,
            on_tool_complete=on_tool_call_complete,
            stream_handler_factory=create_stream_handler  # Enable tool streaming
        ):
            if event.event == "tools_end":
                self._tool_calls_info.extend(event.data.get("execution_results", []))
            
            yield event  # Pure events!
```

## Truncation Policy

Simple, configurable truncation:

```python
# Default: 10,000 character limit
executor = ToolExecutor(
    truncation_policy=TruncationPolicy(max_chars=10000)
)

# Custom limit
executor = ToolExecutor(
    truncation_policy=TruncationPolicy(max_chars=5000)
)

# No truncation (not recommended)
executor = ToolExecutor(
    truncation_policy=TruncationPolicy(max_chars=float('inf'))
)
```

## Execution Modes

```python
# Parallel (default) - all tools execute concurrently
executor = ToolExecutor(execution_mode=ExecutionMode.PARALLEL)

# Sequential - tools execute one by one
executor = ToolExecutor(execution_mode=ExecutionMode.SEQUENTIAL)
```

## Tool Event Streaming

Tools can emit real-time events via `ToolStreamHandler`:

```python
@tool(description="Long-running analysis", category="analysis")
async def analyze_data(*, context: ToolContext, dataset: str):
    """Example tool that emits progress events"""
    
    if context.stream_handler:
        # Emit progress
        await context.stream_handler.emit_progress(0, "Starting analysis...")
        
        # Emit status
        await context.stream_handler.emit_status("processing", "Analyzing dataset")
        
        # Emit log
        await context.stream_handler.emit_log("info", "Processing 1000 records")
        
        # Emit custom event
        await context.stream_handler.emit("custom_event", {"key": "value"})
    
    # Do work...
    result = perform_analysis()
    
    return {"success": True, "data": result}
```

These events are automatically:
1. Queued by ToolExecutor
2. Converted to SSEEvent objects
3. Streamed in real-time to the frontend
4. Formatted as `tool_{event_type}` (e.g., `tool_progress`, `tool_status`)

## Benefits

1. **Clean Code**: No special handling, just `async for event in ...`
2. **Type Safety**: All events are strongly-typed Pydantic models
3. **Reusability**: ToolExecutor is agent-agnostic
4. **Testability**: Easy to test with event collection
5. **Extensibility**: Add new event types without breaking existing code
6. **Consistency**: Same pattern everywhere (LangChain-inspired)

## What Makes This "Event-Driven"

- ✅ Everything yielded is an `SSEEvent` object
- ✅ No magic tuples like `("__tool_messages__", data)`
- ✅ No return values mixed with yields
- ✅ All control flow via event types (`tools_end`, etc.)
- ✅ Async generators all the way down
- ✅ Events flow naturally from inner to outer layers

## Anti-Patterns (What NOT to Do)

```python
# ❌ DON'T: Mix returns and yields
async def bad_execute():
    yield SSEEvent(...)
    return {"tool_messages": [...]}  # Wrong!

# ❌ DON'T: Use magic tuples
async def bad_execute():
    yield ("__tool_messages__", messages)  # Wrong!

# ❌ DON'T: Execute twice
async def bad_execute():
    async for event in executor.execute_batch_streaming(...):
        yield event
    # Don't do this:
    batch = await executor.execute_batch(...)  # Wrong!

# ✅ DO: Pure events only
async def good_execute():
    async for event in executor.execute_batch_streaming(...):
        if event.event == "tools_end":
            # Extract data from event
            results = event.data.get("execution_results", [])
        yield event  # Always forward!
```

## Future Enhancements

Potential additions while maintaining event-driven design:
- Retry policies for failed tools
- Timeout configuration
- Tool dependency chains
- Conditional execution
- Result caching
- Metrics/telemetry events

All would be implemented via new event types and policy objects!

