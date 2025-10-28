# SSE Streaming Pattern for Real-Time Tool Call Updates

## Overview

This document describes the robust Server-Sent Events (SSE) pattern implemented for real-time streaming of tool call updates in the Finch application. This pattern ensures that users see tool calls **as they are being made** (not after completion), providing immediate feedback and a better user experience.

## Architecture

### Flow Diagram

```
User sends message
    ↓
Frontend (ChatContainer.tsx) → Opens SSE stream
    ↓
Backend (/chat/stream endpoint)
    ↓
ChatService.send_message_stream()
    ↓
Agent.process_message_stream()
    ↓
For each tool call:
    1. YIELD tool_call_start event → Frontend shows "Calling..."
    2. Execute tool
    3. YIELD tool_call_complete event → Frontend shows "✓ Completed"
    ↓
YIELD thinking event → Frontend shows "🤔 Analyzing results..."
    ↓
YIELD assistant_message event → Frontend shows final response
    ↓
YIELD done event → Frontend cleanup
```

## Key Components

### 1. Backend SSE Event Models (`backend/models/sse.py`)

Pydantic models for type-safe SSE events:

```python
class SSEEvent(BaseModel):
    """Base SSE event with to_sse_format() method"""
    event: str
    data: Dict[str, Any]

class ToolCallStartEvent(BaseModel):
    """Sent IMMEDIATELY when tool call begins"""
    tool_call_id: str
    tool_name: str
    arguments: Dict[str, Any]
    timestamp: str

class ToolCallCompleteEvent(BaseModel):
    """Sent when tool call finishes"""
    tool_call_id: str
    tool_name: str
    status: Literal["completed", "error"]
    resource_id: Optional[str]
    error: Optional[str]
    timestamp: str

class ThinkingEvent(BaseModel):
    """Sent when AI is analyzing tool results and generating response"""
    message: str
    timestamp: str

class AssistantMessageEvent(BaseModel):
    """The final LLM response"""
    content: str
    timestamp: str
    needs_auth: bool

class DoneEvent(BaseModel):
    """Stream complete signal"""
    message: str
    timestamp: str

class ErrorEvent(BaseModel):
    """Error occurred during processing"""
    error: str
    details: Optional[str]
    timestamp: str
```

### 2. Agent Streaming (`backend/agent.py`)

The `ChatAgent` has two methods:
- `process_message()` - Original non-streaming version (still works for backward compatibility)
- `process_message_stream()` - New streaming version that yields SSE events

**Key Implementation Detail - Tool Call Streaming:**

```python
async def _handle_tool_calls_stream(self, ...):
    for tool_call in tool_calls:
        # 🎯 CRITICAL: Yield START event BEFORE executing tool
        yield SSEEvent(
            event="tool_call_start",
            data=ToolCallStartEvent(
                tool_call_id=tool_call.id,
                tool_name=function_name,
                arguments=function_args
            ).model_dump()
        )
        
        # NOW execute the tool (may take time)
        tool_result = await self._execute_tool(...)
        
        # Yield COMPLETE event after execution
        yield SSEEvent(
            event="tool_call_complete",
            data=ToolCallCompleteEvent(
                tool_call_id=tool_call.id,
                tool_name=function_name,
                status="completed" if success else "error"
            ).model_dump()
        )
```

**Why This Matters:**
- Events are yielded in real-time as they happen
- Frontend receives `tool_call_start` immediately (before tool executes)
- Frontend receives `tool_call_complete` after tool finishes
- This provides live feedback to users

### 3. Chat Service (`backend/modules/chat_service.py`)

Wraps the agent streaming with database context:

```python
async def send_message_stream(self, message: str, chat_id: str, user_id: str):
    """Stream SSE events from agent to frontend"""
    # Get chat history
    # Get user context
    
    async for event in self.agent.process_message_stream(...):
        # Track tool calls for resource creation
        # Yield formatted SSE string
        yield event.to_sse_format()
```

### 4. API Route (`backend/routes/chat.py`)

FastAPI endpoint that returns `StreamingResponse`:

```python
@router.post("/stream")
async def send_chat_message_stream(chat_message: ChatMessage):
    async def event_generator():
        async for sse_data in chat_service.send_message_stream(...):
            yield sse_data
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Important for nginx
        }
    )
```

### 5. Frontend API (`frontend/lib/api.ts`)

TypeScript interfaces and streaming client:

```typescript
export const chatApi = {
  sendMessageStream: (
    message: string,
    userId: string,
    chatId: string,
    handlers: SSEEventHandlers
  ): EventSource => {
    // Uses fetch with ReadableStream (not EventSource)
    // Parses SSE format manually
    // Calls appropriate handler for each event type
    
    fetch('/chat/stream', {
      method: 'POST',
      body: JSON.stringify({ message, session_id: userId, chat_id: chatId })
    }).then(async (response) => {
      const reader = response.body?.getReader();
      // Parse SSE format and call handlers
    });
  }
}
```

**Why not EventSource?**
- `EventSource` only supports GET requests
- We need POST to send message data
- Using `fetch` with `ReadableStream` gives us full control

### 6. Frontend Component (`frontend/components/ChatContainer.tsx`)

React component that displays ephemeral tool call messages:

```typescript
const handleSendMessage = async (content: string) => {
  const toolCallsMap = new Map<string, ToolCallStatus>();
  
chatApi.sendMessageStream(content, userId, chatId, {
  onToolCallStart: (event) => {
    // IMMEDIATELY show "Calling..." message
    const status = { tool_call_id: event.tool_call_id, tool_name: event.tool_name, status: 'calling' };
    toolCallsMap.set(event.tool_call_id, status);
    setEphemeralToolCalls(Array.from(toolCallsMap.values()));
  },
  
  onToolCallComplete: (event) => {
    // Update to "✓ Completed"
    const status = toolCallsMap.get(event.tool_call_id);
    status.status = event.status;
    setEphemeralToolCalls(Array.from(toolCallsMap.values()));
  },
  
  onThinking: (event) => {
    // Show "🤔 Analyzing results..."
    setIsThinking(true);
  },
  
  onAssistantMessage: (event) => {
    // Hide thinking indicator and add final message to chat
    setIsThinking(false);
    setMessages(prev => [...prev, { role: 'assistant', content: event.content }]);
  },
  
  onDone: () => {
    // Cleanup, reload resources
    setTimeout(() => setEphemeralToolCalls([]), 5000);
  }
});
};
```

## Event Lifecycle Example

**User asks:** "What stocks do I own?"

1. **tool_call_start** event:
   ```json
   {
     "event": "tool_call_start",
     "data": {
       "tool_call_id": "call_abc123",
       "tool_name": "get_portfolio",
       "arguments": {},
       "timestamp": "2025-10-28T10:30:00Z"
     }
   }
   ```
   → Frontend immediately shows: 🔧 "get portfolio - Calling function..."

2. **tool_call_complete** event (after ~2 seconds):
   ```json
   {
     "event": "tool_call_complete",
     "data": {
       "tool_call_id": "call_abc123",
       "tool_name": "get_portfolio",
       "status": "completed",
       "resource_id": "res_xyz789",
       "timestamp": "2025-10-28T10:30:02Z"
     }
   }
   ```
   → Frontend updates to: 🔧 "get portfolio - ✓ Completed"

3. **thinking** event (AI is now analyzing the results):
   ```json
   {
     "event": "thinking",
     "data": {
       "message": "Analyzing results...",
       "timestamp": "2025-10-28T10:30:02Z"
     }
   }
   ```
   → Frontend shows: 🤔 "Analyzing results... - AI is processing the information"

4. **assistant_message** event (after ~1 second of AI processing):
   ```json
   {
     "event": "assistant_message",
     "data": {
       "content": "Here's your portfolio: AAPL (50 shares), GOOGL (25 shares)...",
       "timestamp": "2025-10-28T10:30:03Z",
       "needs_auth": false
     }
   }
   ```
   → Frontend displays the final response

5. **done** event:
   ```json
   {
     "event": "done",
     "data": {
       "message": "Stream complete",
       "timestamp": "2025-10-28T10:30:03Z"
     }
   }
   ```
   → Frontend cleans up (after 5 second delay)

## Benefits

### 1. **Real-Time Feedback**
- Users see tool calls **as they start** (not after they finish)
- Reduces perceived latency
- Better UX - users know something is happening

### 2. **Type Safety**
- Pydantic models on backend ensure correct data structure
- TypeScript interfaces on frontend prevent errors
- Compile-time checks catch issues early

### 3. **Scalable**
- Easy to add new event types
- Each event is independent
- Can handle multiple tool calls in parallel

### 4. **Robust Error Handling**
- Errors are streamed as events (not exceptions)
- Frontend can handle errors gracefully
- Partial results still shown even if one tool fails

### 5. **Backward Compatible**
- Original `/chat` endpoint still works
- Can migrate gradually
- No breaking changes

## Usage Pattern

### For New Features

When adding a new tool or feature that needs real-time updates:

1. **Backend**: Use the streaming agent method
   ```python
   async for event in agent.process_message_stream(...):
       yield event
   ```

2. **Frontend**: Use the streaming API
   ```typescript
   chatApi.sendMessageStream(message, userId, chatId, {
     onToolCallStart: (event) => { /* show loading */ },
     onToolCallComplete: (event) => { /* show result */ },
     // ... other handlers
   });
   ```

### Testing

To test the streaming pattern:

1. Start backend: `cd backend && uvicorn main:app --reload`
2. Start frontend: `cd frontend && npm run dev`
3. Send a message that triggers tool calls (e.g., "review my portfolio")
4. Observe the ephemeral messages appearing in real-time

## Best Practices

### 1. Always Yield Start Events First
```python
# ✅ CORRECT
yield tool_call_start_event
result = await execute_tool()
yield tool_call_complete_event

# ❌ WRONG
result = await execute_tool()
yield tool_call_start_event  # Too late!
yield tool_call_complete_event
```

### 2. Use Pydantic Models for All Events
```python
# ✅ CORRECT
yield SSEEvent(
    event="tool_call_start",
    data=ToolCallStartEvent(...).model_dump()
)

# ❌ WRONG
yield f"event: tool_call_start\ndata: {json.dumps({...})}\n\n"
```

### 3. Handle All Event Types in Frontend
```typescript
// ✅ CORRECT
chatApi.sendMessageStream(message, userId, chatId, {
  onToolCallStart: () => {},
  onToolCallComplete: () => {},
  onAssistantMessage: () => {},
  onDone: () => {},
  onError: () => {}  // Don't forget error handling!
});
```

### 4. Clean Up Ephemeral Messages
```typescript
// Show tool calls for a few seconds, then hide
onDone: () => {
  setTimeout(() => setEphemeralToolCalls([]), 5000);
}
```

## Troubleshooting

### Events Not Appearing in Frontend

1. Check backend logs - are events being yielded?
2. Check network tab - is `/chat/stream` responding?
3. Check for buffering issues (nginx, proxy)
4. Verify SSE format is correct (event: ...\ndata: ...\n\n)

### Events Delayed

1. Check if backend is awaiting long-running operations
2. Ensure events are yielded immediately (not batched)
3. Check for proxy buffering (`X-Accel-Buffering: no`)

### Type Errors

1. Ensure Pydantic models match TypeScript interfaces
2. Run type checks: `mypy backend/` and `npm run type-check`
3. Update interfaces when adding new fields

## Future Enhancements

1. **Progress Updates**: Add progress events for long-running tools
2. **Cancellation**: Allow users to cancel in-progress tool calls
3. **Resource Creation**: Stream resource IDs as they're created
4. **Partial Results**: Stream partial results for large datasets
5. **WebSocket Fallback**: Use WebSockets if SSE not supported

## Conclusion

This SSE streaming pattern provides a robust, type-safe, and user-friendly way to stream real-time updates from backend tool calls to the frontend. The key insight is **yielding events when tool calls START** (not just when they finish), which dramatically improves perceived performance and user experience.

