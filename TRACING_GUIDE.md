# Finch Tracing Guide 🔍

This guide explains how to use OpenTelemetry tracing with Jaeger to visualize where time is being spent in your agent interactions.

## Quick Start

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

This will install:
- `opentelemetry-*` packages for tracing
- `opentelemetry-instrumentation-logging` for log correlation
- `opentelemetry-exporter-otlp` for Jaeger export

### 2. Start Jaeger

```bash
./start-jaeger.sh
```

This starts Jaeger UI at: **http://localhost:16686**

### 3. Enable Tracing in Backend

Make sure your `backend/.env` has:
```bash
ENABLE_TIMING_LOGS=true
```

### 4. Restart Backend

```bash
./start-backend.sh
```

### 5. Use Your App

Send a chat message through the UI. The backend will automatically send traces to Jaeger.

### 6. View Traces in Jaeger

1. Open http://localhost:16686
2. Select **finch-api** from the Service dropdown
3. Click **Find Traces**
4. Click on any trace to see the detailed breakdown

## What You'll See 📊

### Trace Hierarchy

```
agent.ChatAgent.interaction (overall request)
├── agent.turn.1 (first iteration)
│   ├── llm.call (LLM request/response)
│   │   └── Events: "First chunk received (TTFB)", "Stream completed"
│   ├── tool.get_portfolio (tool execution)
│   │   └── Events: "Tool invoked", "Tool completed"
│   └── tool.analyze_financials (another tool)
│       └── Events: "Tool invoked", "Tool completed"
├── agent.turn.2 (second iteration if needed)
│   ├── llm.call
│   └── tool.create_plot
└── ...
```

### Key Metrics You Can Track

#### 1. **Agent Turns**
- **Span Name**: `agent.turn.N`
- **What it shows**: How long each agent iteration takes
- **Attributes**:
  - `agent.turn`: Turn number (1, 2, 3, ...)
  - `agent.turn_duration_ms`: Duration of this turn
  - `agent.tool_calls_requested`: Number of tools called
  - `agent.message_count`: Number of messages in context

#### 2. **LLM Calls**
- **Span Name**: `llm.call`
- **What it shows**: Time spent calling the LLM (OpenAI, etc.)
- **Attributes**:
  - `llm.model`: Model used (e.g., "gpt-4o")
  - `llm.streaming`: Whether streaming was used
  - `llm.duration_ms`: Total LLM call duration
  - `llm.ttfb_ms`: Time to first byte (for streaming)
  - `llm.tokens.prompt`: Prompt tokens used
  - `llm.tokens.completion`: Completion tokens used
  - `llm.chunk_count`: Number of chunks streamed
- **Events**:
  - "LLM request started"
  - "First chunk received (TTFB)" - Shows latency to start streaming
  - "Stream completed"

#### 3. **Tool Executions**
- **Span Name**: `tool.TOOLNAME` (e.g., `tool.get_portfolio`)
- **What it shows**: Time spent executing each tool
- **Attributes**:
  - `tool.name`: Tool name
  - `tool.category`: Tool category (e.g., "financial_metrics")
  - `tool.duration_ms`: Execution duration
  - `tool.success`: Whether tool succeeded
  - `user.id`: User who invoked it
- **Events**:
  - "Tool invoked" - Shows arguments (truncated)
  - "Tool completed" - Shows success/failure

### Log Correlation 📝

All logs are now automatically correlated with traces! When you click on a span in Jaeger, you can see the logs that were emitted during that span's execution.

**Look for**:
- `trace_id` and `span_id` in your logs
- Logs appear as events in the Jaeger timeline
- Click "Logs" tab in span details to see related logs

## How to Analyze Performance 🎯

### Find Slow Operations

1. In Jaeger, sort traces by duration (longest first)
2. Click on a slow trace
3. Look at the span timeline to see which operations took the most time:
   - **Wide bars** = slow operations
   - **Nested bars** = child operations (tool calls within agent turns)

### Typical Bottlenecks

#### 1. **Slow LLM Calls**
- **Symptom**: `llm.call` span is wide
- **Check**: 
  - `llm.ttfb_ms` - Is latency to first token slow?
  - `llm.tokens.total` - Are you sending too many tokens?
  - `llm.model` - Is the model slow? (GPT-4 vs GPT-4o)
- **Fix**: 
  - Use faster models for simple tasks
  - Reduce context size
  - Use streaming to improve perceived latency

#### 2. **Slow Tool Calls**
- **Symptom**: `tool.TOOLNAME` span is wide
- **Check**: Which tool is slow?
  - Database queries? (check nested SQLAlchemy spans)
  - API calls? (check nested HTTP spans)
  - Data processing?
- **Fix**: 
  - Cache results
  - Optimize queries
  - Add indexes
  - Use async operations

#### 3. **Multiple Agent Turns**
- **Symptom**: Many `agent.turn.N` spans
- **Check**: Why is the agent looping?
  - Is it making redundant tool calls?
  - Are tool results unclear?
  - Is the agent confused?
- **Fix**:
  - Improve tool descriptions
  - Add examples to system prompt
  - Simplify tool interfaces

### Example Analysis Session

```
1. Find trace for a slow request (e.g., 8 seconds)
2. See it has 3 agent turns

Turn 1 (2s):
  ├── llm.call: 1.5s (ttfb: 200ms) ✅ OK
  └── tool.get_portfolio: 400ms ✅ OK

Turn 2 (5s):
  ├── llm.call: 500ms ✅ OK
  └── tool.analyze_financials: 4.5s ⚠️ SLOW!
      └── Check tool logs/events for details

Turn 3 (1s):
  └── llm.call: 900ms ✅ OK (final response)

Conclusion: analyze_financials tool is the bottleneck (4.5s out of 8s)
```

## Viewing Traces in Different Ways

### 1. **Timeline View** (Default)
Shows spans as horizontal bars over time. Best for seeing:
- Overall duration
- Sequential vs parallel operations
- Bottlenecks

### 2. **Trace Graph View**
Shows spans as a hierarchical graph. Best for:
- Understanding call hierarchy
- Seeing parent-child relationships
- Complex traces with many spans

### 3. **Trace Statistics View**
Shows aggregated statistics. Best for:
- Comparing multiple traces
- Finding patterns
- Identifying outliers

## Advanced Features

### Custom Span Attributes

You can add custom attributes to spans in your code:

```python
from utils.tracing import add_span_attributes, add_span_event

# Add attributes to current span
add_span_attributes({
    "custom.metric": 123,
    "user.name": "alice"
})

# Add event to current span (shows up as log in timeline)
add_span_event("Custom event", {
    "detail": "Something interesting happened"
})
```

### Manual Spans

Create custom spans for specific operations:

```python
from utils.tracing import get_tracer

tracer = get_tracer(__name__)

with tracer.start_as_current_span("my_operation") as span:
    # Do work
    result = expensive_function()
    
    # Add attributes
    span.set_attribute("result.size", len(result))
```

## Troubleshooting

### Traces Not Appearing?

1. **Check Jaeger is running**: `docker ps | grep jaeger`
2. **Check backend config**: `ENABLE_TIMING_LOGS=true` in `.env`
3. **Check backend logs**: Should see "OpenTelemetry tracing enabled"
4. **Check Jaeger endpoint**: Backend sends to `http://localhost:4318/v1/traces`

### Jaeger UI Empty?

1. Make sure you've selected **finch-api** as the service
2. Try adjusting the time range (default is last 1 hour)
3. Click "Find Traces" to refresh
4. Check "Lookback" dropdown (try "Last 15 minutes")

### Performance Impact?

OpenTelemetry has minimal overhead:
- ~1-2% CPU increase
- ~10-20MB memory increase
- Batched exports (not blocking)
- Can be disabled with `ENABLE_TIMING_LOGS=false`

## Stopping Jaeger

```bash
./stop-jaeger.sh
```

Or manually:
```bash
docker stop jaeger
docker rm jaeger
```

## Production Considerations

For production use:
1. Use a persistent backend (not all-in-one)
2. Configure sampling (don't trace 100% of requests)
3. Export to production observability platform (Datadog, Honeycomb, etc.)
4. Set appropriate retention policies
5. Add authentication to Jaeger UI

## Summary

With this tracing setup, you can now:
- ✅ See exactly where time is spent in each request
- ✅ Identify slow agent turns vs slow tool calls
- ✅ Track LLM latency and token usage
- ✅ Correlate logs with trace spans
- ✅ Optimize based on real data, not guesses

Happy tracing! 🚀

