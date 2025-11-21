# SSE Events Guide

This document describes all the Server-Sent Events (SSE) that the backend streams to the frontend during chat interactions.

## Event Types

### 1. `assistant_message_delta`
Streamed LLM response text, one chunk at a time.

```json
{
  "event": "assistant_message_delta",
  "data": {
    "delta": "Here is some text..."
  }
}
```

### 2. `tool_call_start`
Emitted when a tool begins execution.

```json
{
  "event": "tool_call_start",
  "data": {
    "tool_call_id": "call_abc123",
    "tool_name": "analyze_financials",
    "arguments": {"symbols": ["AAPL", "MSFT"], "objective": "Compare companies"},
    "timestamp": "2025-11-20T19:35:00.000Z"
  }
}
```

### 3. `tool_status`
Real-time status updates from tools showing what they're doing.

```json
{
  "event": "tool_status",
  "data": {
    "status": "executing|fetching|analyzing|completed|error|thinking",
    "message": "Fetching Income Statement for AAPL...",
    "timestamp": "2025-11-20T19:35:01.000Z"
  }
}
```

**Examples:**
- `"status": "executing", "message": "Analyzing AAPL, MSFT..."`
- `"status": "fetching", "message": "Fetching Income Statement for AAPL..."`
- `"status": "completed", "message": "✓ Retrieved 50 records"`
- `"status": "error", "message": "✗ API error: 404 Not Found"`
- `"status": "thinking", "message": "Analyzing data and preparing response..."`

### 4. `tool_log`
Log messages from tools with severity levels.

```json
{
  "event": "tool_log",
  "data": {
    "level": "info|warning|error|debug",
    "message": "✓ Found 10 positions in your portfolio",
    "timestamp": "2025-11-20T19:35:02.000Z"
  }
}
```

### 5. `tool_progress`
Progress updates for long-running tools (0-100%).

```json
{
  "event": "tool_progress",
  "data": {
    "percent": 45.5,
    "message": "Processed 45 of 100 items",
    "timestamp": "2025-11-20T19:35:03.000Z"
  }
}
```

### 6. `tool_call_complete`
Emitted when a tool finishes execution.

```json
{
  "event": "tool_call_complete",
  "data": {
    "tool_call_id": "call_abc123",
    "tool_name": "analyze_financials",
    "status": "completed|error",
    "timestamp": "2025-11-20T19:35:05.000Z"
  }
}
```

### 7. `thinking`
Shown between tool execution and final response generation.

```json
{
  "event": "thinking",
  "data": {
    "message": "Processing results and formulating response...",
    "timestamp": "2025-11-20T19:35:06.000Z"
  }
}
```

### 8. `assistant_message`
Final complete message from assistant (after streaming).

```json
{
  "event": "assistant_message",
  "data": {
    "content": "Here's the analysis...",
    "timestamp": "2025-11-20T19:35:10.000Z",
    "needs_auth": false
  }
}
```

### 9. `done`
Stream complete marker.

```json
{
  "event": "done",
  "data": {
    "message": "Stream complete",
    "timestamp": "2025-11-20T19:35:11.000Z"
  }
}
```

### 10. `error`
Error occurred during processing.

```json
{
  "event": "error",
  "data": {
    "error": "Error message",
    "details": "Detailed error information",
    "timestamp": "2025-11-20T19:35:12.000Z"
  }
}
```

## Typical Event Flow

### Simple Query (No Tools)
```
1. assistant_message_delta (streaming text chunks)
2. assistant_message (final complete message)
3. done
```

### Query with Single Tool
```
1. assistant_message_delta (may be empty if tool call immediately)
2. tool_status ("Calling get_portfolio...")
3. tool_call_start
4. tool_status ("Retrieving portfolio from connected brokerage...")
5. tool_log ("✓ Found 10 positions in your portfolio")
6. tool_status ("✓ Portfolio retrieved")
7. tool_call_complete
8. thinking ("Processing results...")
9. tool_status ("Analyzing data and preparing response...")
10. assistant_message_delta (streaming response about portfolio)
11. assistant_message (final message)
12. done
```

### Query with Multiple Parallel Tools (Financial Analysis)
```
1. assistant_message_delta (optional initial response)
2. tool_status ("Analyzing AAPL, MSFT...")
3. tool_call_start (analyze_financials)
4. tool_status ("Starting financial analysis...")
   
   [Sub-agent executes multiple get_fmp_data calls in parallel]
   
5. tool_status ("Fetching Income Statement for AAPL...")
6. tool_status ("Fetching Balance Sheet for MSFT...")
7. tool_status ("Fetching Key Metrics for AAPL...")
8. tool_log ("✓ Retrieved 50 Income Statement records")
9. tool_log ("✓ Retrieved 1 Key Metrics records")
10. tool_status ("✓ Retrieved 40 records")
11. tool_status ("✓ Financial analysis completed")
12. tool_call_complete (analyze_financials)
13. thinking ("Processing results...")
14. assistant_message_delta (streaming analysis)
15. assistant_message (final message)
16. done
```

## Status Messages by Tool

### `get_portfolio`
- **Start**: "Retrieving your portfolio..."
- **Progress**: "Retrieving portfolio from connected brokerage..."
- **Complete**: "✓ Found X positions in your portfolio"

### `analyze_financials`
- **Start**: "Analyzing AAPL, MSFT..." (or "Starting financial analysis...")
- **Progress**: Various sub-tool status messages
- **Complete**: "✓ Financial analysis completed"

### `get_fmp_data`
- **Start**: "Fetching Income Statement for AAPL..."
- **Complete**: "✓ Retrieved 50 Income Statement records"
- **Error**: "✗ API error: 404 Not Found"

### `create_plot`
- **Start**: "Creating visualization..."
- **Progress**: "Generating visualization..."
- **Complete**: "✓ Visualization created"

### `get_reddit_trending_stocks`
- **Start**: "Scanning r/wallstreetbets for top 10 trending stocks..."
- **Complete**: "✓ Retrieved trending stocks"

## Frontend Implementation

### Handling Events

```typescript
const eventSource = new EventSource('/chat/stream');

eventSource.addEventListener('tool_status', (event) => {
  const data = JSON.parse(event.data);
  // Show status in UI: data.status, data.message
  console.log(`[${data.status}] ${data.message}`);
});

eventSource.addEventListener('tool_log', (event) => {
  const data = JSON.parse(event.data);
  // Show log with appropriate styling based on data.level
  console.log(`[${data.level}] ${data.message}`);
});

eventSource.addEventListener('tool_progress', (event) => {
  const data = JSON.parse(event.data);
  // Update progress bar: data.percent
  updateProgressBar(data.percent, data.message);
});

eventSource.addEventListener('assistant_message_delta', (event) => {
  const data = JSON.parse(event.data);
  // Append delta to message display
  appendToMessage(data.delta);
});

eventSource.addEventListener('done', () => {
  // Close connection, hide progress indicators
  eventSource.close();
});
```

### UI Suggestions

1. **Status Bar**: Show current `tool_status` message prominently
2. **Activity Log**: Scrollable list of `tool_log` messages
3. **Progress Indicator**: Use `tool_progress` for long operations
4. **Tool Cards**: Show each `tool_call_start` as a card that updates with status
5. **Thinking Indicator**: Animated indicator during `thinking` event

## Testing

To test all events, try these queries:

1. **Simple**: "What is 2+2?" (no tools, just text streaming)
2. **Single Tool**: "Show me my portfolio" (get_portfolio)
3. **Multiple Parallel Tools**: "Compare AAPL and MSFT" (analyze_financials → multiple get_fmp_data calls)
4. **With Errors**: "Analyze INVALID_TICKER" (shows error status events)
5. **Long Operation**: "Analyze insider activity for my entire portfolio" (shows progress)

## Debugging

- **Missing Events**: Check that stream_handler is properly passed to all tools
- **Events Not Appearing**: Verify frontend EventSource is handling all event types
- **Delayed Events**: Tool events are queued and yielded after each base agent event
- **Duplicate Events**: Make sure frontend doesn't re-register listeners

## Backend Architecture

```
ChatAgent.process_message_stream()
  ├── Creates ToolStreamHandler with callback
  ├── Sets agent_context.stream_handler
  │
  └── BaseAgent.run_tool_loop_streaming()
      ├── Calls LLM (yields assistant_message_delta events)
      ├── Detects tool calls
      ├── Calls on_tool_call_start() → yields tool_status + tool_call_start
      │
      ├── BaseAgent._execute_tools_step()
      │   ├── Tools execute with context.stream_handler
      │   │   ├── Tool calls stream_handler.emit_status() → callback → queue
      │   │   └── Tool calls stream_handler.emit_log() → callback → queue
      │   │
      │   └── Calls on_tool_call_complete() → yields tool_status + tool_call_complete
      │
      ├── Queued tool events are yielded after each base agent event
      └── Calls on_thinking() → yields thinking + tool_status
```

## Summary

With this enhanced SSE event system, the frontend can show users:
- ✅ **Real-time progress** for every operation
- ✅ **Detailed status updates** from all tools
- ✅ **Error messages** when things fail
- ✅ **Log messages** for debugging
- ✅ **Progress bars** for long operations
- ✅ **Tool execution timeline** showing what's happening when

This creates a transparent, responsive UX where users always know what the agent is doing! 🎉

