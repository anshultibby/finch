# Backend Architecture - Clean & DRY

## Overview

The backend follows a **layered architecture** with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (SSE)                        │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│                      Routes (FastAPI)                        │
│               chat.py, snaptrade.py, resources.py            │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│                      ChatService                             │
│         Orchestrates: DB, Agents, Resources, SSE             │
└───────────┬──────────────────────────────────┬──────────────┘
            │                                  │
┌───────────▼───────────┐          ┌──────────▼──────────────┐
│   ChatAgent (Main)    │          │  PlottingAgent (Sub)    │
│  - Streams to user    │          │  - Creates charts       │
│  - Calls tools        │◄─────────┤  - Delegate pattern     │
│  - Uses BaseAgent     │          │  - Uses BaseAgent       │
└───────────┬───────────┘          └─────────────────────────┘
            │
┌───────────▼───────────────────────────────────────────────┐
│                      BaseAgent                            │
│  - run_tool_loop() - Non-streaming                        │
│  - run_tool_loop_streaming() - Streaming                  │
│  - Tool execution orchestration                           │
└───────────┬───────────────────────────────────────────────┘
            │
┌───────────▼───────────────────────────────────────────────┐
│                      ToolRunner                           │
│  - execute() - Single tool execution                      │
│  - execute_multiple() - Batch execution                   │
│  - Error handling, logging, context management            │
└───────────┬───────────────────────────────────────────────┘
            │
┌───────────▼───────────────────────────────────────────────┐
│                    ToolRegistry                           │
│  - get_tool() - Lookup by name                            │
│  - get_openai_tools() - Get schemas for LLM               │
│  - Storage: Dict[str, Tool]                               │
└───────────┬───────────────────────────────────────────────┘
            │
┌───────────▼───────────────────────────────────────────────┐
│                      Tools                                │
│  @tool decorated functions with business logic            │
│  get_portfolio, create_chart, analyze_data, etc.          │
└───────────────────────────────────────────────────────────┘
```

## Layer Responsibilities

### 1. **Routes** (FastAPI endpoints)
- **File**: `routes/chat.py`, `routes/snaptrade.py`, etc.
- **Responsibility**: HTTP interface, request validation
- **Does**: Receive requests, call services, return responses
- **Does NOT**: Business logic, tool execution, DB access

### 2. **ChatService**
- **File**: `modules/chat_service.py`
- **Responsibility**: Orchestrate chat flow
- **Does**: 
  - Manage chat sessions
  - Call agents
  - Save messages to DB
  - Create resources from tool results
  - Stream SSE events to frontend
- **Does NOT**: Execute tools directly, LLM calls

### 3. **Agents** (ChatAgent, PlottingAgent)
- **Files**: `modules/agent/chat_agent.py`, `modules/agent/plotting_agent.py`
- **Responsibility**: LLM interaction, tool orchestration
- **Does**:
  - Build prompts
  - Call LLM with streaming
  - Decide when to call tools
  - Handle tool results
  - **ChatAgent**: Has custom streaming loop (not using BaseAgent yet, by design)
  - **PlottingAgent**: Uses BaseAgent.run_tool_loop() (simple, no streaming needed)
- **Does NOT**: Execute tools (delegates to ToolRunner), DB access

**Note**: ChatAgent could be refactored to use BaseAgent's streaming, but has special requirements:
- Auth status checking
- Tool call tracking for resources
- Custom truncation logic
- Frontend SSE events

### 4. **BaseAgent**
- **File**: `modules/agent/base_agent.py`
- **Responsibility**: Reusable agent logic
- **Does**:
  - `run_tool_loop()` - Non-streaming tool execution loop
  - `run_tool_loop_streaming()` - Streaming tool execution loop
  - Message building
  - Tool call accumulation
- **Does NOT**: Tool execution (delegates to ToolRunner)

### 5. **ToolRunner**
- **File**: `modules/tools/runner.py`
- **Responsibility**: Tool execution
- **Does**:
  - Execute single tool
  - Execute multiple tools
  - Build context (session_id, user_id, stream_handler)
  - Error handling and logging
  - Validate arguments
- **Does NOT**: Tool discovery (uses ToolRegistry)

### 6. **ToolRegistry**
- **File**: `modules/tools/registry.py`
- **Responsibility**: Tool storage and lookup
- **Does**:
  - Register tools
  - Lookup by name
  - Filter by category/auth
  - Generate OpenAI schemas
- **Does NOT**: Execute tools (done by ToolRunner)

### 7. **Tools**
- **Files**: `modules/tool_definitions.py`, `modules/*_tools.py`
- **Responsibility**: Business logic
- **Does**:
  - Implement specific functionality
  - Return structured results
  - Optionally stream progress via `context.stream_handler`
- **Does NOT**: LLM calls, database access (uses injected dependencies)

## Data Flow

### User Message → Response

```
1. User sends message
   └─> POST /api/chat/stream

2. Route calls ChatService
   └─> chat_service.process_message_stream()

3. ChatService calls ChatAgent
   └─> chat_agent.process_message_stream()

4. ChatAgent has custom streaming loop
   └─> Calls LLM with streaming
   └─> Yields SSE events to frontend
   └─> LLM decides to call tool

5. ChatAgent calls ToolRunner
   └─> tool_runner.execute()

6. ToolRunner looks up tool in ToolRegistry
   └─> tool_registry.get_tool()

7. ToolRunner executes tool function
   └─> Tool runs business logic
   └─> Optionally emits progress via stream_handler

8. Tool returns result to ToolRunner
   └─> ToolRunner logs and validates

9. Result flows back to ChatAgent
   └─> Agent adds to messages
   └─> Loops back to LLM

10. LLM generates final response
    └─> Agent streams to ChatService

11. ChatService saves to DB
    └─> Creates resources
    └─> Streams SSE to frontend

12. Frontend receives and displays
```

## Key Design Patterns

### 1. **Delegation Pattern** (Agents)
```python
# Main agent delegates to sub-agent
create_plot tool → PlottingAgent → create_chart tool
```
**Benefit**: Specialized agents for complex tasks

### 2. **Registry Pattern** (Tools)
```python
# Central registry, agents specify what they need
tool_registry.get_openai_tools(tool_names=['create_chart'])
```
**Benefit**: Single source of truth, flexible tool subsets

### 3. **Observer Pattern** (Streaming)
```python
# Tools optionally emit progress
if context.stream_handler:
    await context.stream_handler.emit_progress(50, "Halfway")
```
**Benefit**: Optional streaming without breaking existing tools

### 4. **Strategy Pattern** (Execution)
```python
# Different execution strategies
tool_runner.execute()  # Standard
base_agent.run_tool_loop()  # With LLM loop
base_agent.run_tool_loop_streaming()  # With streaming
```
**Benefit**: Flexible execution modes

## DRY Principles Applied

### ❌ Before (Duplicated)
```python
# tool_executor.py
async def execute_tool():
    context = ToolContext(session_id=session_id)
    result = await tool_registry.execute_tool(...)
    
# BaseAgent
async def run_tool_loop():
    context = ToolContext(session_id=session_id)
    result = await tool_registry.execute_tool(...)
    
# ChatAgent
async def process_message():
    context = ToolContext(session_id=session_id)
    result = await tool_registry.execute_tool(...)
```

### ✅ After (DRY)
```python
# ToolRunner (single source of truth)
async def execute():
    context = ToolContext(session_id=session_id)
    # ... error handling, logging, validation
    result = await tool.handler(**kwargs)

# Everyone uses ToolRunner
tool_executor: await tool_runner.execute(...)
BaseAgent: await tool_runner.execute(...)
ChatAgent: await tool_runner.execute(...)  # via tool_executor
```

## Module Dependencies

```
Routes → ChatService
ChatService → ChatAgent, CRUD, Resources
ChatAgent → ToolRunner (directly, custom streaming)
PlottingAgent → BaseAgent → ToolRunner
BaseAgent → ToolRunner, ToolRegistry
ToolRunner → ToolRegistry
ToolRegistry → Tools
Tools → Business logic (APIs, calculations, etc.)
```

**Key Rules:**
- Lower layers NEVER import upper layers
- Each layer has single responsibility
- Dependencies flow downward
- Use dependency injection (context, session_id)

## File Organization

```
backend/
├── routes/              # HTTP endpoints
│   ├── chat.py
│   ├── snaptrade.py
│   └── resources.py
│
├── modules/
│   ├── chat_service.py          # Orchestration
│   │
│   ├── agent/                   # Agents
│   │   ├── base_agent.py       # Reusable agent logic
│   │   ├── chat_agent.py       # Main user-facing agent
│   │   ├── plotting_agent.py   # Specialized sub-agent
│   │   └── tool_executor.py    # Backward compat wrapper
│   │
│   ├── tools/                   # Tool system
│   │   ├── __init__.py
│   │   ├── decorator.py        # @tool decorator
│   │   ├── models.py           # Tool, ToolContext
│   │   ├── registry.py         # ToolRegistry (storage)
│   │   ├── runner.py           # ToolRunner (execution)
│   │   └── stream_handler.py   # ToolStreamHandler (progress)
│   │
│   ├── tool_definitions.py      # Tool declarations
│   ├── snaptrade_tools.py       # Business logic
│   ├── apewisdom_tools.py
│   ├── insider_trading_tools.py
│   └── plotting_tools.py
│
├── crud/                # Database operations
├── models/              # Pydantic/SQLAlchemy models
└── services/            # Utilities (encryption, etc.)
```

## Testing Strategy

### Unit Tests
```python
# Test tools in isolation
result = await tool_func(context=ToolContext(), ...)
assert result["success"]

# Test ToolRunner
result = await tool_runner.execute("get_portfolio", {}, session_id="test")
assert result["success"]

# Test BaseAgent
agent = PlottingAgent()
messages = agent.build_messages("Create chart")
result = await agent.run_tool_loop(messages)
assert result["success"]
```

### Integration Tests
```python
# Test full flow
async with AsyncClient(app=app) as client:
    response = await client.post("/api/chat/stream", json={
        "message": "Show my portfolio",
        "session_id": "test"
    })
    assert response.status_code == 200
```

## Performance Considerations

1. **Tool Execution**: ~100-500ms per tool
2. **LLM Calls**: ~1-3s streaming
3. **Database**: ~10-50ms per query
4. **SSE Streaming**: ~5ms per event

**Optimizations:**
- Async/await throughout
- Streaming responses (don't wait for completion)
- Tool result truncation (50KB limit)
- Connection pooling (DB, HTTP)

## Error Handling

**Layers handle errors differently:**

1. **Tools**: Return `{"success": False, "error": "..."}`
2. **ToolRunner**: Catches exceptions, returns error dict
3. **BaseAgent**: Handles tool errors, continues loop
4. **ChatAgent**: Streams error events to frontend
5. **Routes**: HTTP error codes (500, 400, etc.)

**Never crashes user-facing code!**

## ChatAgent vs BaseAgent

**Current State:**
- **ChatAgent**: Custom streaming loop (process_message_stream)
  - ✅ Works perfectly for user-facing chat
  - ✅ Handles SSE events, auth status, resource tracking
  - ✅ Special logic for portfolio truncation
  - ❌ Doesn't reuse BaseAgent's streaming (by design)

- **PlottingAgent**: Uses BaseAgent.run_tool_loop()
  - ✅ Minimal code (~20 lines)
  - ✅ No streaming needed (fast execution)
  - ✅ Perfect for sub-agents

**Why ChatAgent doesn't use BaseAgent yet:**
1. **Special Requirements**: Auth status, tool tracking, custom truncation
2. **SSE Events**: Custom event types for frontend
3. **Working Code**: Current implementation is stable and tested
4. **Clear Interface**: Easy to understand and modify

**Could ChatAgent use BaseAgent?** YES, with callbacks:
```python
async def on_content_delta(delta):
    yield SSEEvent(event="assistant_message_delta", data={"delta": delta})

async def on_tool_call_start(info):
    yield SSEEvent(event="tool_call_start", data=ToolCallStartEvent(...))

await base_agent.run_tool_loop_streaming(
    messages,
    on_content_delta=on_content_delta,
    on_tool_call_start=on_tool_call_start,
    ...
)
```

**Recommendation**: Keep current architecture
- ✅ Clean separation: ChatAgent (complex) vs PlottingAgent (simple)
- ✅ Both work great
- ✅ Easy to refactor later if needed
- ✅ BaseAgent useful for new simple agents

## Future Improvements

- [ ] Optionally refactor ChatAgent to use BaseAgent (low priority)
- [ ] Add tool result caching
- [ ] Tool execution telemetry
- [ ] Parallel tool execution
- [ ] Tool dependency graphs
- [ ] Circuit breakers for failing tools
- [ ] Tool versioning
- [ ] Tool streaming progress to frontend (ToolStreamHandler → SSE)

## Summary

✅ **Single Responsibility** - Each layer does one thing  
✅ **DRY** - ToolRunner eliminates duplication  
✅ **Testable** - Clear boundaries, dependency injection  
✅ **Extensible** - New tools/agents easy to add  
✅ **Observable** - Logging, streaming, progress  
✅ **Type-safe** - Pydantic throughout  

The architecture is **clean, maintainable, and scalable**!

