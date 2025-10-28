# SSE Quick Reference Guide

## When to Use SSE vs Regular API

### Use SSE Streaming (`/chat/stream`) When:
✅ You want real-time feedback as tool calls execute  
✅ You want to show progress to users  
✅ You have long-running operations  
✅ You want better perceived performance  

### Use Regular API (`/chat`) When:
✅ You need synchronous responses  
✅ You're doing simple non-tool operations  
✅ You need simpler error handling  
✅ You don't need real-time updates  

## Code Snippets

### Backend: Creating a New SSE Event Type

```python
# In backend/models/sse.py
class MyNewEvent(BaseModel):
    """Description of your event"""
    my_field: str
    my_number: int
    timestamp: str = datetime.now().isoformat()

# Don't forget to add to __init__.py exports!
```

### Backend: Yielding Events in Agent

```python
# In agent streaming method
yield SSEEvent(
    event="my_event_type",
    data=MyNewEvent(
        my_field="value",
        my_number=42
    ).model_dump()
)
```

### Frontend: Adding Event Handler

```typescript
// In api.ts - add interface
export interface SSEMyNewEvent {
  my_field: string;
  my_number: number;
  timestamp: string;
}

// In SSEEventHandlers
export interface SSEEventHandlers {
  // ... existing handlers
  onMyEvent?: (event: SSEMyNewEvent) => void;
}

// In sendMessageStream - add case
switch (eventType) {
  // ... existing cases
  case 'my_event_type':
    handlers.onMyEvent?.(eventData as SSEMyNewEvent);
    break;
}
```

### Frontend: Using in Component

```typescript
chatApi.sendMessageStream(message, userId, chatId, {
  onToolCallStart: (event) => {
    console.log('Tool started:', event.tool_name);
    // Show loading indicator
  },
  onToolCallComplete: (event) => {
    console.log('Tool completed:', event.tool_name, event.status);
    // Update UI
  },
  onThinking: (event) => {
    console.log('AI is thinking:', event.message);
    // Show thinking indicator
    setIsThinking(true);
  },
  onMyEvent: (event) => {
    console.log('My event:', event.my_field);
    // Handle your custom event
  },
  onAssistantMessage: (event) => {
    // Hide thinking indicator
    setIsThinking(false);
    // Add message to chat
  },
  onDone: () => {
    // Cleanup
  },
  onError: (event) => {
    // Handle errors
  }
});
```

## Event Timing Cheat Sheet

```
Event Order Timeline:
═══════════════════════════════════════════════════════════════

User sends message
    ↓ 0ms
[tool_call_start] ← IMMEDIATELY (before execution)
    ↓
Backend executes tool (e.g., API call, database query)
    ↓ 2000ms (example)
[tool_call_complete] ← After execution finishes
    ↓
[thinking] ← AI is analyzing tool results
    ↓
LLM generates response
    ↓ 1000ms (example)
[assistant_message] ← Final response
    ↓
[done] ← Stream complete
```

## Common Patterns

### Pattern 1: Single Tool Call
```
tool_call_start → tool_call_complete → thinking → assistant_message → done
```

### Pattern 2: Multiple Tool Calls
```
tool_call_start (tool 1) → tool_call_complete (tool 1)
→ tool_call_start (tool 2) → tool_call_complete (tool 2)
→ thinking → assistant_message → done
```

### Pattern 3: Recursive Tool Calls (Agent calls more tools)
```
tool_call_start (tool 1) → tool_call_complete (tool 1)
→ tool_call_start (tool 2) → tool_call_complete (tool 2)
→ thinking → tool_call_start (tool 3) → tool_call_complete (tool 3)
→ thinking → assistant_message → done
```

### Pattern 4: Error Handling
```
tool_call_start → tool_call_complete (status: error)
→ assistant_message (error message) → done

OR

tool_call_start → [error] → done
```

## Debugging Tips

### Backend Not Streaming?
```bash
# Check if events are being yielded
# Look for console logs:
# "🔧 Executing tool: <name>"
# "📨 STREAMING MESSAGE for session: <id>"

# Test the endpoint directly:
curl -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message":"test","session_id":"user-123","chat_id":"chat-123"}'
```

### Frontend Not Receiving Events?
```javascript
// Add debug logging
chatApi.sendMessageStream(message, userId, chatId, {
  onToolCallStart: (event) => {
    console.log('[DEBUG] tool_call_start:', event);
  },
  onToolCallComplete: (event) => {
    console.log('[DEBUG] tool_call_complete:', event);
  },
  onAssistantMessage: (event) => {
    console.log('[DEBUG] assistant_message:', event);
  },
  onDone: (event) => {
    console.log('[DEBUG] done:', event);
  },
  onError: (event) => {
    console.error('[DEBUG] error:', event);
  }
});

// Check browser Network tab:
// - Is /chat/stream responding?
// - Is Content-Type: text/event-stream?
// - Are events arriving in real-time?
```

### Events Delayed/Buffered?
```python
# Check backend headers in routes/chat.py
return StreamingResponse(
    event_generator(),
    media_type="text/event-stream",
    headers={
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",  # ← IMPORTANT for nginx
    }
)
```

## Performance Considerations

### Keep Events Small
✅ Only send necessary data in events  
✅ Don't include full tool results in events  
✅ Use resource_id references instead  

### Don't Over-Stream
✅ Send events when status changes (not constantly)  
✅ Batch similar events if appropriate  
✅ Use reasonable update intervals  

### Clean Up
✅ Clear ephemeral messages after delay  
✅ Close streams when component unmounts  
✅ Handle network errors gracefully  

## Security Considerations

### Backend
✅ Validate user_id and chat_id  
✅ Check authentication before streaming  
✅ Rate limit SSE endpoints  
✅ Don't expose sensitive data in events  

### Frontend
✅ Verify event source (origin)  
✅ Sanitize event data before rendering  
✅ Handle malformed events gracefully  
✅ Implement timeout for abandoned streams  

## Testing Checklist

- [ ] Tool calls appear immediately when started
- [ ] Tool calls update when completed
- [ ] Multiple tool calls work correctly
- [ ] Errors are handled gracefully
- [ ] Ephemeral messages clear after delay
- [ ] Resources are created and linked
- [ ] Network errors are caught
- [ ] Browser console shows no errors
- [ ] Events arrive in correct order
- [ ] Stream closes properly on done

## Common Issues & Solutions

### Issue: Events arrive all at once at the end
**Solution**: Ensure you're yielding events BEFORE tool execution, not after

### Issue: Frontend not updating in real-time
**Solution**: Check if you're calling `setEphemeralToolCalls()` in each handler

### Issue: "Stream already consumed" error
**Solution**: Don't try to read the stream multiple times - use the handlers

### Issue: Events not parsing correctly
**Solution**: Verify SSE format is exact: `event: <type>\ndata: <json>\n\n`

### Issue: Connection drops randomly
**Solution**: Add keep-alive pings or implement reconnection logic

## Useful Commands

```bash
# Test SSE endpoint with curl
curl -N -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message":"test","session_id":"user-123","chat_id":"chat-123"}'

# Watch backend logs
tail -f backend/logs/app.log

# Check if port is listening
lsof -i :8000

# Test with httpie (prettier output)
http --stream POST localhost:8000/chat/stream message=test session_id=user-123 chat_id=chat-123
```

## Resources

- **Full Documentation**: `SSE_STREAMING_PATTERN.md`
- **Implementation Summary**: `SSE_IMPLEMENTATION_SUMMARY.md`
- **MDN SSE Reference**: https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events
- **FastAPI Streaming**: https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse

