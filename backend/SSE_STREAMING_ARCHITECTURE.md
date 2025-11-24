# SSE Streaming Architecture

## Overview

The system streams real-time updates from tools to the frontend using Server-Sent Events (SSE). This allows users to see progress updates, status messages, and logs as tools execute.

## Architecture Flow

```
┌─────────────┐
│  Frontend   │  Listens for SSE events
│  (React)    │  onToolStatus, onToolProgress, onToolLog
└──────┬──────┘
       │ fetch(/chat/stream)
       ↓
┌─────────────┐
│   FastAPI   │  POST /chat/stream
│   Route     │  Yields SSE formatted strings
└──────┬──────┘
       │
       ↓
┌─────────────┐
│ ChatService │  send_message_stream()
│             │  Creates AgentContext with stream_handler
└──────┬──────┘
       │
       ↓
┌─────────────┐
│  BaseAgent  │  process_message_stream()
│             │  Yields SSE events
└──────┬──────┘
       │
       ↓
┌─────────────┐
│ ToolExecutor│  execute_batch_streaming()
│             │  Creates stream_handler_factory for each tool
└──────┬──────┘
       │
       ↓
┌─────────────┐
│   Tool      │  Receives context.stream_handler
│ (async def) │  await context.stream_handler.emit_status(...)
└──────┬──────┘
       │
       ↓
┌─────────────┐
│   Client    │  Business logic (e.g., SnapTrade API calls)
│ (async def) │  await stream_handler.emit_status(...)
│             │  await stream_handler.emit_progress(...)
└─────────────┘
```

## Key Components

### 1. ToolStreamHandler (`modules/tools/stream_handler.py`)

The handler that tools use to emit events:

```python
class ToolStreamHandler:
    async def emit_status(self, status: str, message: Optional[str] = None)
    async def emit_progress(self, percent: float, message: Optional[str] = None)
    async def emit_log(self, level: str, message: str)
```

### 2. Tool Execution Context (`modules/agent/context.py`)

Tools receive context with a stream_handler:

```python
class AgentContext:
    user_id: str
    chat_id: str
    stream_handler: ToolStreamHandler  # Tools use this to emit events
    data: Optional[Dict[str, Any]] = None
```

### 3. Tool Executor (`modules/tools/executor.py`)

Creates stream handlers that convert tool events to SSE:

```python
async def execute_batch_streaming(
    self,
    tool_calls: List[ToolCallRequest],
    context: AgentContext,
    enable_tool_streaming: bool = True
) -> AsyncGenerator[SSEEvent, None]:
```

When `enable_tool_streaming=True`:
- Creates a stream_handler_factory
- Each tool gets a ToolStreamHandler with a callback that queues SSE events
- Events are streamed in real-time via asyncio.Queue

### 4. SSE Events (`models/sse.py`)

Events are formatted as SSE and sent to frontend:

```
event: tool_status
data: {"type": "status", "status": "fetching", "message": "...", "tool_call_id": "...", "tool_name": "..."}

event: tool_progress
data: {"type": "progress", "percent": 50, "message": "...", "tool_call_id": "...", "tool_name": "..."}

event: tool_log
data: {"type": "log", "level": "info", "message": "...", "tool_call_id": "...", "tool_name": "..."}
```

## How to Add Streaming to a Tool

### Step 1: Make Tool Async

```python
@tool(description="...", category="...")
async def my_tool(*, context: AgentContext, param: str) -> Dict[str, Any]:
    # Tool implementation
```

### Step 2: Emit Status Updates

```python
async def my_tool(*, context: AgentContext, param: str):
    # Emit initial status
    await context.stream_handler.emit_status("starting", "Initializing...")
    
    # Do some work
    data = await fetch_data()
    
    # Emit progress
    await context.stream_handler.emit_progress(50, "Processing data...")
    
    # More work
    result = await process_data(data)
    
    # Emit completion
    await context.stream_handler.emit_status("completed", "✓ Done!")
    
    return {"success": True, "data": result}
```

### Step 3: Pass Stream Handler to Client Code

If your tool calls a client/service that does long-running work:

```python
# Tool definition
async def my_tool(*, context: AgentContext, param: str):
    result = await my_client.do_work(
        param=param,
        stream_handler=context.stream_handler  # ← Pass it through!
    )
    return result

# Client code
class MyClient:
    async def do_work(self, param: str, stream_handler: Optional[ToolStreamHandler] = None):
        if stream_handler:
            await stream_handler.emit_status("fetching", "Connecting to API...")
        
        # Run blocking API call in executor to avoid blocking event loop
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.sync_api_call(param)
        )
        
        if stream_handler:
            await stream_handler.emit_status("processing", "Parsing response...")
        
        result = parse_response(response)
        
        if stream_handler:
            await stream_handler.emit_log("info", f"✓ Processed {len(result)} items")
        
        return result
```

## Frontend Integration

The frontend listens for SSE events in `lib/api.ts`:

```typescript
chatApi.sendMessageStream(message, userId, chatId, {
  onToolStatus: (event) => {
    // Update UI with status message
    setToolStatusMessages(prev => {
      const next = new Map(prev);
      next.set(event.tool_call_id, event.message || event.status);
      return next;
    });
  },
  
  onToolProgress: (event) => {
    // Update UI with progress
    const progressText = `${Math.round(event.percent)}%`;
    setToolStatusMessages(prev => {
      const next = new Map(prev);
      next.set(event.tool_call_id, progressText);
      return next;
    });
  },
  
  onToolLog: (event) => {
    // Optional: Display logs in UI
    console.log(`[${event.level}]`, event.message);
  }
});
```

## What We Fixed

### Problem

The `get_portfolio` tool was only emitting 1 event even though tool streaming was enabled:

```python
# OLD CODE - Only 1 event emitted
async def get_portfolio(*, context: AgentContext):
    await context.stream_handler.emit_status("fetching", "...")  # ← Event 1
    
    result = snaptrade_tools.get_portfolio(user_id=context.user_id)  # ← Synchronous, blocks for 4+ seconds, no events!
    
    return result
```

### Solution

1. Made `snaptrade_tools.get_portfolio()` async
2. Passed `stream_handler` to the client
3. Client emits events during API calls:

```python
# NEW CODE - Multiple events throughout execution
async def get_portfolio(*, context: AgentContext):
    result = await snaptrade_tools.get_portfolio(
        user_id=context.user_id,
        stream_handler=context.stream_handler  # ← Pass it through!
    )
    return result

# In snaptrade.py
async def get_portfolio(self, user_id: str, stream_handler: Optional[ToolStreamHandler] = None):
    if stream_handler:
        await stream_handler.emit_status("initializing", "Checking connection...")
    
    accounts = await self._get_accounts(user_id, secret, stream_handler)
    
    for idx, account_id in enumerate(account_ids, 1):
        if stream_handler:
            await stream_handler.emit_progress(idx/total * 100, f"Account {idx}/{total}...")
        
        positions = await self._get_positions_for_account(account_id, stream_handler)
    
    if stream_handler:
        await stream_handler.emit_status("completed", "✓ Done!")
    
    return portfolio
```

## Benefits

1. **Real-time feedback**: Users see progress as tools execute
2. **Better UX**: No more "black box" waiting periods
3. **Debugging**: Logs help troubleshoot issues
4. **Non-blocking**: Using async/await ensures other tools can run concurrently

## Best Practices

1. **Always make tools async**: `async def my_tool(...)`
2. **Pass stream_handler down**: Client code should receive and use it
3. **Use run_in_executor for blocking calls**: Wrap synchronous API calls to avoid blocking
4. **Emit meaningful updates**: Status at start/end, progress for long operations
5. **Check if handler exists**: `if stream_handler: await stream_handler.emit_status(...)`

## Testing

Enable tool streaming in chat_service.py:

```python
agent = BaseAgent(
    context=agent_context,
    system_prompt=FINCH_SYSTEM_PROMPT,
    model=Config.LLM_MODEL,
    tool_names=tool_names,
    enable_tool_streaming=True  # ← Must be True!
)
```

Check logs for streaming activity:

```
INFO | modules.tools.executor | 🌊 Tool streaming ENABLED for 1 tool(s)
INFO | modules.tools.executor | Executing 1 tool(s) in parallel
DEBUG | modules.tools.executor | 📤 Tool event: get_portfolio → status: initializing
DEBUG | modules.tools.executor | 📤 Tool event: get_portfolio → status: fetching
DEBUG | modules.tools.executor | 📤 Tool event: get_portfolio → progress: 50%
INFO | modules.tools.executor | 🌊 Tool streaming complete: 5 events emitted  ← Should be > 1!
```

Check browser console for received events:

```
📊 Tool status: get_portfolio initializing Checking connection...
📊 Tool status: get_portfolio fetching Connecting to brokerage...
📈 Tool progress: get_portfolio 50% Processing account 1/2...
📊 Tool status: get_portfolio completed ✓ Retrieved 10 position(s)
```

