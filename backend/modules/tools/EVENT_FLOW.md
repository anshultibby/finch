# Tool SSE Event Flow - Complete Trace

## Overview

This document traces how SSE events flow from tools all the way to the frontend, showing the complete event-driven architecture.

## Event Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ TOOL                                                             │
│                                                                  │
│  @tool(description="Long operation")                            │
│  async def my_tool(*, context: ToolContext, data: list):        │
│      # Tool emits events                                        │
│      await context.stream_handler.emit_progress(50, "Working")  │
│      await context.stream_handler.emit("options", {...})        │
│      return ToolSuccess(data=result)                            │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             │ event: {"type": "progress", ...}
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│ TOOL STREAM HANDLER (created by ToolExecutor)                   │
│                                                                  │
│  stream_callback(event):                                        │
│      sse_event = SSEEvent(                                      │
│          event=f"tool_{event['type']}",  # "tool_progress"      │
│          data=event                                             │
│      )                                                           │
│      await tool_events_queue.put(sse_event)                     │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             │ SSEEvent
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│ TOOL EXECUTOR (execute_batch_streaming)                         │
│                                                                  │
│  while tools running:                                           │
│      sse_event = await tool_events_queue.get()                  │
│      yield sse_event  ← Stream to agent                         │
│                                                                  │
│  # When tools complete:                                         │
│  yield SSEEvent(event="tools_end", data={...})                  │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             │ SSEEvent (all events)
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│ AGENT (_execute_tools_step)                                     │
│                                                                  │
│  async for event in executor.execute_batch_streaming(...):      │
│      if event.event == "tools_end":                             │
│          # Extract tracking info                                │
│          self._tool_calls_info.extend(event.data["results"])    │
│      yield event  ← Forward to agent loop                       │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             │ SSEEvent (all events)
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│ AGENT (run_tool_loop_streaming)                                 │
│                                                                  │
│  async for event in self._execute_tools_step(...):              │
│      yield event  ← Forward to service                          │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             │ SSEEvent (all events)
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│ CHAT SERVICE (process_message_stream)                           │
│                                                                  │
│  async for event in agent.process_message_stream(...):          │
│      yield event.to_sse_format()  ← Forward to route            │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             │ SSE formatted string
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│ ROUTE (/chat/stream)                                            │
│                                                                  │
│  async for sse_text in chat_service.process(...):               │
│      await response.write(sse_text)  ← Write to HTTP stream     │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             │ HTTP SSE stream
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│ FRONTEND (EventSource)                                          │
│                                                                  │
│  eventSource.addEventListener("tool_progress", (event) => {     │
│      const data = JSON.parse(event.data);                       │
│      updateUI(data);  // Show progress bar                      │
│  });                                                             │
│                                                                  │
│  eventSource.addEventListener("tool_options", (event) => {      │
│      const data = JSON.parse(event.data);                       │
│      showOptions(data.options);  // Show buttons                │
│  });                                                             │
└─────────────────────────────────────────────────────────────────┘
```

## Event Types

### 1. Tool Events (from tools via stream_handler)

```python
# Tool emits:
await context.stream_handler.emit_progress(50, "Processing...")
# → {"type": "progress", "percent": 50, "message": "Processing...", ...}

await context.stream_handler.emit("options", {
    "question": "Choose portfolio",
    "options": [...]
})
# → {"type": "options", "question": "...", "options": [...], ...}
```

### 2. SSE Events (executor converts)

```python
# Executor converts to:
SSEEvent(
    event="tool_progress",  # Prefixed with "tool_"
    data={
        "type": "progress",
        "percent": 50,
        "message": "Processing...",
        "tool_call_id": "call_abc",
        "tool_name": "my_tool",
        "timestamp": "2024-..."
    }
)
```

### 3. SSE Format (sent to frontend)

```
event: tool_progress
data: {"type":"progress","percent":50,"message":"Processing..."}

event: tool_options
data: {"type":"options","question":"...","options":[...]}

event: tools_end
data: {"tool_messages":[...],"execution_results":[...]}
```

## Code Example

### Tool Implementation

```python
from modules.tools import tool, ToolContext, ToolSuccess

@tool(description="Process data with progress", category="processing")
async def process_data(*, context: ToolContext, items: list) -> ToolSuccess:
    """Tool that streams progress events"""
    
    total = len(items)
    processed = []
    
    # Emit initial progress
    if context.stream_handler:
        await context.stream_handler.emit_progress(0, "Starting...")
    
    for i, item in enumerate(items):
        # Process item
        result = process_item(item)
        processed.append(result)
        
        # Emit progress every 10%
        if i % (total // 10) == 0 and context.stream_handler:
            percent = (i / total) * 100
            await context.stream_handler.emit_progress(
                percent,
                f"Processed {i}/{total} items"
            )
    
    # Emit final progress
    if context.stream_handler:
        await context.stream_handler.emit_progress(100, "Complete!")
    
    return ToolSuccess(
        data=processed,
        message=f"Processed {total} items successfully"
    )
```

### Agent Usage

```python
# BaseAgent - NO tool streaming
async for event in self._tool_executor.execute_batch_streaming(
    tool_calls=requests,
    context=context,
    enable_tool_streaming=False  # Only start/complete/end events
):
    yield event

# ChatAgent - WITH tool streaming
async for event in self._tool_executor.execute_batch_streaming(
    tool_calls=requests,
    context=context,
    enable_tool_streaming=True  # ALL events including tool progress/status/options
):
    yield event
```

### Executor Implementation (simplified)

```python
async def execute_batch_streaming(
    self,
    tool_calls: List[ToolCallRequest],
    context: ToolContext,
    enable_tool_streaming: bool = False
):
    """
    Executor handles ALL streaming complexity internally.
    Agents just pass enable_tool_streaming flag.
    """
    # Create queue if streaming enabled
    tool_events_queue = asyncio.Queue() if enable_tool_streaming else None
    
    # Create stream handler factory if streaming enabled
    if enable_tool_streaming:
        def create_stream_handler(tool_call_id, tool_name):
            async def callback(event):
                # Convert tool event to SSE
                sse_event = SSEEvent(
                    event=f"tool_{event['type']}",
                    data=event
                )
                await tool_events_queue.put(sse_event)
            
            return ToolStreamHandler(callback=callback, ...)
        
        stream_handler_factory = create_stream_handler
    else:
        stream_handler_factory = None
    
    # Execute tools in background
    tools_task = asyncio.create_task(self._execute_parallel(...))
    
    # Stream queued events in real-time
    if tool_events_queue:
        while not tools_task.done():
            try:
                event = await asyncio.wait_for(tool_events_queue.get(), timeout=0.1)
                yield event  # Stream to agent
            except asyncio.TimeoutError:
                continue
        
        # Drain remaining events
        while not tool_events_queue.empty():
            yield tool_events_queue.get_nowait()
    
    # Wait for completion
    results = await tools_task
    
    # Emit final event
    yield SSEEvent(event="tools_end", data={...})
```

## Key Design Points

### 1. No Factory Complexity for Agents
✅ **Before (complex):**
```python
# Agent had to create factory
def create_stream_handler(tool_call_id, tool_name):
    async def callback(event):
        # Complex callback logic
        await queue.put(event)
    return ToolStreamHandler(callback=callback, ...)

async for event in executor.execute_batch_streaming(
    ...,
    stream_handler_factory=create_stream_handler  # Agent provides factory
):
    yield event
```

✅ **After (simple):**
```python
# Agent just passes a flag
async for event in executor.execute_batch_streaming(
    ...,
    enable_tool_streaming=True  # That's it!
):
    yield event
```

### 2. Executor Owns All Complexity
- Queue creation
- Stream handler factory creation
- Event conversion (dict → SSEEvent)
- Real-time streaming loop
- Queue draining

### 3. Pure Event Flow
- Everything is an `SSEEvent`
- No callbacks to manage
- No queues to create
- Just `async for event in ...`

### 4. Type Safety
- `SSEEvent` is a Pydantic model
- Tool events have defined structure
- Compile-time checking

## Testing Event Flow

```python
import asyncio
from modules.tools import ToolExecutor, ToolContext, ToolCallRequest

async def test_tool_streaming():
    """Test that tool events flow correctly"""
    executor = ToolExecutor()
    context = ToolContext(user_id="test_user")
    
    # Create tool call
    call = ToolCallRequest(
        id="call_123",
        name="process_data",
        arguments={"items": [1, 2, 3, 4, 5]}
    )
    
    # Collect all events
    events = []
    async for event in executor.execute_batch_streaming(
        tool_calls=[call],
        context=context,
        enable_tool_streaming=True  # Enable streaming
    ):
        events.append(event)
        print(f"Event: {event.event}")
        
        # Check for tool progress events
        if event.event == "tool_progress":
            print(f"  Progress: {event.data['percent']}%")
        
        # Check for options events
        if event.event == "tool_options":
            print(f"  Options: {event.data['question']}")
    
    # Verify event types
    event_types = [e.event for e in events]
    assert "tool_progress" in event_types  # Tool emitted progress
    assert "tools_end" in event_types       # Executor emitted end
    
    print(f"✅ Received {len(events)} events")
```

## Summary

**Complete SSE Flow:**
1. Tool emits → `stream_handler.emit()`
2. Executor queues → `tool_events_queue.put()`
3. Executor streams → `yield SSEEvent`
4. Agent forwards → `yield event`
5. Service forwards → `yield event.to_sse_format()`
6. Route writes → HTTP stream
7. Frontend receives → EventSource event

**Key Points:**
- ✅ Pure event-driven (no callbacks at agent level)
- ✅ Simplified agent code (just a flag)
- ✅ Executor handles complexity
- ✅ Events flow unchanged through all layers
- ✅ Type-safe throughout

