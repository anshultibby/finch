# Final Tool Execution Architecture

## Core Philosophy

**Tools own everything about their execution.**

- **Tools** emit status, progress, errors, custom events
- **Executor** handles orchestration (parallel execution, queueing, final event)
- **Agents** just forward events (no special logic)

## Clean Separation

```
┌──────────────────────────────────────────────────────────────┐
│ TOOL                                                          │
│ • Returns: ToolResponse (enforced by decorator)              │
│ • Emits: Status, progress, options, custom events            │
│ • Controls: What, when, how to stream                        │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│ EXECUTOR                                                      │
│ • Executes: Tools in parallel/sequential                     │
│ • Queues: Tool-emitted events                                │
│ • Emits: tools_end event with results                        │
│ • Truncates: Only as safety (10K char limit)                 │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│ AGENT                                                         │
│ • Forwards: All events unchanged                             │
│ • Extracts: Results from tools_end                           │
│ • NO custom logic for tools                                  │
└──────────────────────────────────────────────────────────────┘
```

## What Each Layer Does

### Tools
```python
@tool(description="Fetch market data")
async def get_market_data(*, context: ToolContext, symbol: str):
    # Tool emits its own status
    if context.stream_handler:
        await context.stream_handler.emit_status("fetching", f"Fetching data for {symbol}")
    
    data = fetch_data(symbol)
    
    if context.stream_handler:
        await context.stream_handler.emit_status("processing", f"Processing {len(data)} records")
    
    # Tool decides to truncate
    if len(data) > 100:
        data = data[:100]
    
    # Tool emits completion
    if context.stream_handler:
        await context.stream_handler.emit_status("complete", f"Retrieved {len(data)} records")
    
    # Tool formats its own response
    return DataResponse(
        data=data,
        message=f"Successfully fetched data for {symbol}"
    )
```

### Executor
```python
async def execute_batch_streaming(
    self,
    tool_calls: List[ToolCallRequest],
    context: ToolContext,
    enable_tool_streaming: bool = False  # Simple flag!
):
    # Create queue if streaming enabled
    if enable_tool_streaming:
        tool_events_queue = asyncio.Queue()
        stream_handler_factory = create_handler_factory(tool_events_queue)
    
    # Execute tools
    tools_task = asyncio.create_task(self._execute_parallel(...))
    
    # Stream tool events in real-time
    if tool_events_queue:
        while not tools_task.done():
            event = await tool_events_queue.get()
            yield event  # Forward tool events
    
    results = await tools_task
    
    # Emit final event with results
    yield SSEEvent(
        event="tools_end",
        data={
            "tool_messages": [...],      # For LLM
            "execution_results": [...]   # For tracking
        }
    )
```

### Base Agent
```python
async def _execute_tools_step(self, tool_calls, context, ...):
    # Parse calls
    requests = [ToolCallRequest(...) for tc in tool_calls]
    
    # Execute with streaming
    async for event in self._tool_executor.execute_batch_streaming(
        tool_calls=requests,
        context=context,
        enable_tool_streaming=False  # No tool events
    ):
        if event.event == "tools_end":
            # Extract tracking info
            self._tool_calls_info.extend(event.data["execution_results"])
        
        yield event  # Just forward
```

### Chat Agent
```python
async def _execute_tools_step(self, tool_calls, context, ...):
    # Parse calls
    requests = [ToolCallRequest(...) for tc in tool_calls]
    
    # Execute with streaming ENABLED
    async for event in self._tool_executor.execute_batch_streaming(
        tool_calls=requests,
        context=context,
        enable_tool_streaming=True  # Enable tool events!
    ):
        if event.event == "tools_end":
            self._tool_calls_info.extend(event.data["execution_results"])
        
        yield event  # Just forward

# Chat agent has NO custom tool callbacks!
# Tools handle everything themselves.
```

## Event Flow (Complete)

### 1. Tool Execution Starts
```
Executor → [No special event, tools will emit]
```

### 2. Tool Emits Events
```python
# Tool decides what to emit
await context.stream_handler.emit_status("fetching", "Getting data...")
```
```
→ SSEEvent(event="tool_status", data={...})
→ Queued by executor
→ Streamed to agent
→ Forwarded to frontend
```

### 3. Tool Completes
```python
# Tool returns result
return DataResponse(data=data, message="Done")
```
```
Executor converts to tool message for LLM
```

### 4. All Tools Complete
```
Executor → SSEEvent(event="tools_end", data={
    tool_messages: [...],      # For LLM conversation
    execution_results: [...]   # For agent tracking
})
```

## What We Removed

### ❌ Removed: Agent-level tool status
```python
# OLD (BAD)
async def on_tool_call_start(info):
    if info["tool_name"] == "get_fmp_data":
        yield SSEEvent("tool_status", {"message": "Fetching FMP data..."})
    elif info["tool_name"] == "get_portfolio":
        yield SSEEvent("tool_status", {"message": "Getting portfolio..."})
```

**Why:** Agent shouldn't know about tool internals.

### ❌ Removed: Agent-level completion messages
```python
# OLD (BAD)
async def on_tool_call_complete(info):
    if info["tool_name"] == "get_fmp_data":
        yield SSEEvent("tool_status", {"message": f"✓ Retrieved {len(data)} records"})
```

**Why:** Tool already emitted its own completion status.

### ❌ Removed: needs_auth special case
```python
# OLD (BAD)
if result.get("needs_auth"):
    needs_auth[0] = True
```

**Why:** If a tool needs auth, it should return an error in its ToolError response.

### ❌ Removed: Custom stream handler factory in chat_agent
```python
# OLD (BAD)
def create_stream_handler(tool_call_id, tool_name):
    async def callback(event):
        # Complex queuing logic
        await queue.put(event)
    return ToolStreamHandler(callback=callback, ...)
```

**Why:** Executor handles this internally now.

## What We Kept

### ✅ LLM streaming
```python
async def on_content_delta(delta: str):
    yield SSEEvent(event="assistant_message_delta", data={"delta": delta})
```

**Why:** This is about LLM output, not tools.

### ✅ Thinking indicator
```python
async def on_thinking():
    yield SSEEvent(event="thinking", data={"message": "Processing..."})
```

**Why:** This is orchestration-level status between tool execution and LLM response.

### ✅ Tool streaming flag
```python
enable_tool_streaming=True  # Chat agent
enable_tool_streaming=False # Base agent
```

**Why:** Simple, clean way to control streaming behavior.

## Benefits of Final Design

### 1. Zero Agent Logic for Tools
```python
# Chat agent's _execute_tools_step is now TINY
async def _execute_tools_step(self, tool_calls, context, ...):
    requests = [ToolCallRequest(...) for tc in tool_calls]
    async for event in self._tool_executor.execute_batch_streaming(
        tool_calls=requests,
        context=context,
        enable_tool_streaming=True
    ):
        if event.event == "tools_end":
            self._tool_calls_info.extend(event.data["execution_results"])
        yield event
```

### 2. Tools Have Full Control
```python
# Tool decides everything
@tool(description="My tool")
async def my_tool(*, context: ToolContext):
    # Tool emits start status
    if context.stream_handler:
        await context.stream_handler.emit_status("starting", "Initializing...")
    
    # Tool does work
    result = do_work()
    
    # Tool emits completion
    if context.stream_handler:
        await context.stream_handler.emit_status("complete", "Done!")
    
    # Tool formats response
    return ToolSuccess(data=result, message="Success!")
```

### 3. Executor is Pure Orchestration
- Executes tools (parallel/sequential)
- Queues events if streaming enabled
- Applies safety truncation
- Emits final tools_end event
- NO domain knowledge

### 4. Events Flow Unchanged
```
Tool → StreamHandler → Queue → Executor → Agent → Service → Route → Frontend
```

Every layer just forwards - no transformations.

## Summary Table

| Concern | Owner |
|---------|-------|
| What to return | Tool |
| What to emit | Tool |
| When to emit | Tool |
| Status messages | Tool |
| Progress updates | Tool |
| Error messages | Tool |
| Data truncation | Tool (executor has safety limit) |
| Response format | Tool (via ToolResponse) |
| LLM formatting | Tool (via to_llm_content()) |
| ─────────────── | ───────── |
| Parallel execution | Executor |
| Event queuing | Executor |
| Safety truncation | Executor |
| Final tools_end | Executor |
| ─────────────── | ───────── |
| Event forwarding | Agent |
| Result tracking | Agent |
| Loop orchestration | Agent |

**Clean, simple, and scalable.**

