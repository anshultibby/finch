# Tool Responsibility Model

## Philosophy

**Tools own their output.** The executor is just orchestration - tools decide what they return and how.

## Tool Responsibilities

### 1. Output Format
Tools control their own output structure:

```python
@tool(description="Get portfolio data")
async def get_portfolio(*, context: ToolContext):
    """Tool decides its output format"""
    portfolio = fetch_portfolio(context.user_id)
    
    # Tool chooses what to return
    return {
        "success": True,
        "data": portfolio,
        "summary": "Portfolio retrieved",
        # Tool can include any fields it wants
    }
```

### 2. Data Truncation
Tools should truncate their own data if needed:

```python
@tool(description="Fetch large dataset")
async def fetch_market_data(*, context: ToolContext, symbol: str):
    """Tool handles its own truncation"""
    data = fetch_all_data(symbol)  # Might be huge
    
    # Tool decides what to keep
    if len(data) > 100:
        data = data[:100]
        truncated = True
    else:
        truncated = False
    
    return {
        "success": True,
        "data": data,
        "truncated": truncated,
        "total_records": len(data)
    }
```

### 3. Error Handling
Tools format their own errors:

```python
@tool(description="Analyze data")
async def analyze(*, context: ToolContext, dataset: str):
    """Tool handles errors its way"""
    try:
        result = perform_analysis(dataset)
        return {
            "success": True,
            "data": result
        }
    except ValidationError as e:
        return {
            "success": False,
            "error": "Invalid dataset",
            "details": str(e),
            "help": "Please provide a valid dataset name"
        }
```

### 4. Streaming Events
Tools control what events they emit:

```python
@tool(description="Long-running task")
async def process_data(*, context: ToolContext, data: list):
    """Tool decides what to stream"""
    if context.stream_handler:
        # Tool chooses what events to emit
        await context.stream_handler.emit_progress(0, "Starting...")
        
        for i, item in enumerate(data):
            process(item)
            
            # Tool decides when to emit progress
            if i % 10 == 0:
                await context.stream_handler.emit_progress(
                    (i / len(data)) * 100,
                    f"Processed {i}/{len(data)}"
                )
        
        # Tool can emit custom events
        await context.stream_handler.emit("custom", {"key": "value"})
    
    return {"success": True, "processed": len(data)}
```

### 5. Message Format for LLM
Tools can format their output specifically for the LLM:

```python
@tool(description="Get stock price")
async def get_stock_price(*, context: ToolContext, symbol: str):
    """Tool formats output for LLM readability"""
    price = fetch_price(symbol)
    
    return {
        "success": True,
        "data": {
            "symbol": symbol,
            "price": price,
            "currency": "USD"
        },
        # Tool provides LLM-friendly summary
        "message": f"{symbol} is trading at ${price} USD"
    }
```

## Executor Responsibilities

The executor is **minimal** - it just orchestrates:

### 1. Execute Tools
```python
# Executor just calls the tool
result = await runner.execute(tool_name, arguments, context)
```

### 2. Safety Truncation
As a **last resort safety mechanism** only:

```python
# Only if tool returns HUGE result (10K+ chars)
if len(json.dumps(result)) > MAX_CHARS:
    truncated = result[:MAX_CHARS] + "... [TRUNCATED]"
```

This is a safety net, not the primary truncation mechanism.

### 3. Event Orchestration
```python
# Emit start events
yield SSEEvent(event="tool_call_start", ...)

# Execute tool
result = await execute_tool(...)

# Emit complete events
yield SSEEvent(event="tool_call_complete", ...)

# Emit final event
yield SSEEvent(event="tools_end", data={"tool_messages": [...]})
```

### 4. Format for OpenAI API
Convert tool results to OpenAI's expected format:

```python
# Executor formats for OpenAI conversation
tool_message = {
    "role": "tool",
    "tool_call_id": call_id,
    "name": tool_name,
    "content": json.dumps(result)  # Tool's result as-is
}
```

## What Executor Does NOT Do

❌ **Decide what data to keep** - Tool's responsibility
❌ **Transform tool output** - Tool decides format
❌ **Add metadata** - Tool adds what it needs
❌ **Interpret results** - Tool provides interpretation
❌ **Filter fields** - Tool returns what matters

## Benefits

### 1. Tools Have Full Control
- Tool knows its domain best
- Tool decides what's important
- Tool optimizes for its use case

### 2. Executor Stays Simple
- Just orchestration logic
- No domain-specific knowledge
- Easy to understand and maintain

### 3. Flexibility
- Each tool can have different output format
- Tools can evolve independently
- No central "schema" to maintain

### 4. Performance
- Tools truncate early (before serialization)
- No unnecessary data processing
- Tools can stream incrementally

## Example: Smart Tool Truncation

```python
@tool(description="Get insider trades")
async def get_insider_trades(*, context: ToolContext, symbol: str, limit: int = 50):
    """Tool handles pagination and truncation intelligently"""
    
    # Fetch data
    all_trades = fetch_insider_trades(symbol)
    
    # Tool decides how to truncate
    if len(all_trades) > limit:
        trades = all_trades[:limit]
        message = f"Showing {limit} of {len(all_trades)} trades. Use limit parameter for more."
    else:
        trades = all_trades
        message = f"Found {len(trades)} trades"
    
    # Tool provides context
    return {
        "success": True,
        "data": trades,
        "message": message,
        "total_available": len(all_trades),
        "returned": len(trades),
        # Tool can suggest next action
        "suggestion": "Fetch more trades with limit=100" if len(all_trades) > limit else None
    }
```

## Migration Guide

### Old Way (Executor-Heavy)
```python
# ❌ Executor decides truncation
result = tool.execute()
truncated = executor.smart_truncate(result)  # Bad!
```

### New Way (Tool-First)
```python
# ✅ Tool decides output
@tool(...)
async def my_tool(...):
    data = get_data()
    
    # Tool truncates if needed
    if len(data) > 100:
        data = data[:100]
    
    # Tool formats output
    return {
        "success": True,
        "data": data,
        "note": "Truncated to 100 items"
    }

# Executor just executes
result = await executor.execute(tool)  # Simple!
```

## Safety Net

Executor still applies **safety truncation** to prevent catastrophic failures:

```python
# If tool accidentally returns 1MB of data
if len(serialized) > 10_000:  # 10K chars
    # Last resort truncation
    truncated = serialized[:10_000] + "... [TRUNCATED]"
    logger.warning(f"Tool {name} exceeded size limit")
```

But this should be **rare** - tools should manage their own output size.

## Summary

| Concern | Owner |
|---------|-------|
| What to return | **Tool** |
| How to format | **Tool** |
| What to truncate | **Tool** |
| Error messages | **Tool** |
| Streaming events | **Tool** |
| Execution order | Executor |
| Event orchestration | Executor |
| Safety truncation | Executor (last resort) |
| OpenAI formatting | Executor |

**Tool knows best. Executor just coordinates.**

