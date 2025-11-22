# Agent Loop Design Analysis

Comparing our implementation with LangChain's agent loop patterns.

## Current Architecture (Our Implementation)

### Core Loop Structure
```python
# base_agent.py: run_tool_loop_streaming()
while iteration < max_iterations:
    # 1. Call LLM (with streaming)
    content, tool_calls = await _stream_llm_step(messages, tools)
    
    # 2. Check if done
    if not tool_calls:
        return content
    
    # 3. Execute tools (parallel)
    tool_messages = await _execute_tools_step(tool_calls, context)
    
    # 4. Add results to conversation
    messages.extend(tool_messages)
    # Loop continues...
```

### Strengths
✅ Clean ReAct (Reason-Act-Observe) pattern
✅ Good separation: BaseAgent (logic) vs ChatAgent (interface)
✅ Native streaming support throughout
✅ Parallel tool execution with asyncio
✅ Comprehensive OpenTelemetry tracing

### Areas for Improvement

#### 1. Tracing Noise in Core Loop (~40% of the loop code)
**Current:**
```python
while iteration < max_iterations:
    with tracer.start_as_current_span(f"agent.turn.{iteration}"):
        turn_start_time = time.time()
        add_span_attributes({"agent.turn": iteration, ...})
        add_span_event(f"Turn {iteration} started", {...})
        
        # ... actual logic ...
        
        turn_duration_ms = (time.time() - turn_start_time) * 1000
        add_span_attributes({"agent.turn_duration_ms": turn_duration_ms})
```

**Suggestion:** Extract tracing to decorator or context manager
```python
@traced_agent_loop
async def run_tool_loop_streaming(...):
    while iteration < max_iterations:
        with self._trace_turn(iteration):
            # Clean logic only
            ...
```

#### 2. Awkward Event Forwarding Pattern
**Current:**
```python
async for event in self._stream_llm_step(...):
    if isinstance(event, tuple) and event[0] == "__result__":
        _, content, tool_calls = event
    else:
        yield event
```

**Issue:** Magic strings (`"__result__"`, `"__tool_messages__"`) are fragile

**Suggestion:** Use proper types
```python
@dataclass
class LLMStepResult:
    content: str
    tool_calls: List[Dict]
    events: List[SSEEvent]  # Already emitted

result = await self._stream_llm_step(...)
for event in result.events:
    yield event
content, tool_calls = result.content, result.tool_calls
```

#### 3. Callback Overload
**Current:** 4 different callbacks passed through layers
- `on_content_delta`
- `on_tool_call_start`
- `on_tool_call_complete`
- `on_thinking`

**LangChain approach:** Single callback manager
```python
class AgentCallbacks:
    async def on_llm_delta(self, delta: str): ...
    async def on_tool_start(self, tool: str, args: dict): ...
    async def on_tool_end(self, tool: str, result: dict): ...
    async def on_agent_action(self, action: AgentAction): ...
```

#### 4. Missing Error Recovery
**Current:** Exceptions bubble up and kill the loop

**LangChain has:**
- `max_execution_time`: Timeout for entire loop
- `early_stopping_method`: What to do when max iterations hit
  - "force" - Return best answer so far
  - "generate" - Ask LLM to summarize
- `handle_parsing_errors`: Retry with error feedback

**Suggestion:**
```python
async def run_tool_loop_streaming(
    ...,
    max_iterations: int = 10,
    max_execution_time: Optional[float] = None,
    on_max_iterations: Literal["error", "force", "generate"] = "error"
):
    start_time = time.time()
    
    while iteration < max_iterations:
        # Check timeout
        if max_execution_time and (time.time() - start_time) > max_execution_time:
            if on_max_iterations == "force":
                yield SSEEvent(event="warning", data={"message": "Timeout - returning partial result"})
                return
            # ... handle other cases
        
        try:
            # ... normal loop logic ...
        except ToolExecutionError as e:
            # Option to retry or continue with error message
            messages.append({
                "role": "tool",
                "content": f"Error: {e}. Try a different approach."
            })
            continue  # Let LLM try to recover
```

## LangChain's Key Patterns We Should Consider

### 1. Agent State Management
LangChain explicitly tracks agent state:
```python
@dataclass
class AgentState:
    intermediate_steps: List[Tuple[AgentAction, str]]  # History of (action, observation)
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
```

We implicitly track state in `messages` list. Consider explicit state object for better introspection.

### 2. Tool Error Handling
```python
@tool
def my_tool(x: int) -> str:
    """My tool description"""
    try:
        return do_something(x)
    except Exception as e:
        return f"Error: {str(e)}"  # Return error as string, don't raise
```

LangChain tools return errors as strings so the agent can see them and adjust strategy.

### 3. Prompt Template Management
```python
prompt = ChatPromptTemplate.from_messages([
    ("system", "{system_prompt}"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),  # Tool calls go here
])
```

Our `build_messages()` does similar work but could be more explicit about the "scratchpad" section.

### 4. Runnable Interface
LangChain everything is a `Runnable` with `.invoke()`, `.stream()`, `.batch()`. 
Very clean interface we could consider:

```python
class BaseAgent(Runnable):
    async def invoke(self, input: dict) -> dict:
        # Non-streaming
        ...
    
    async def stream(self, input: dict) -> AsyncGenerator[SSEEvent, None]:
        # Streaming (current run_tool_loop_streaming)
        ...
    
    async def batch(self, inputs: list) -> list:
        # Process multiple inputs
        ...
```

## Recommended Changes (Priority Order)

### High Priority
1. **Extract tracing decorators** - Reduce loop complexity by 40%
2. **Add timeout & max_iterations handling** - Better production reliability
3. **Tool error recovery** - Let agent see errors and retry

### Medium Priority
4. **Replace magic strings with types** - Better type safety
5. **Consolidate callbacks** - Single callback manager class

### Low Priority
6. **Runnable interface** - Standardize agent interface
7. **Explicit state object** - Better introspection/debugging

## Example: Cleaned Up Loop

```python
@traced_agent_loop(span_name="agent.interaction")
async def run_tool_loop_streaming(
    self,
    initial_messages: List[Dict],
    context: AgentContext,
    max_iterations: int = 10,
    max_execution_time: Optional[float] = 300.0,  # 5 min default
    llm_config: Optional[LLMConfig] = None,
    callbacks: Optional[AgentCallbacks] = None
) -> AsyncGenerator[SSEEvent, None]:
    """Clean agent loop with proper error handling"""
    
    messages = initial_messages.copy()
    self._reset_state()
    start_time = time.time()
    
    for iteration in range(1, max_iterations + 1):
        # Check timeout
        if max_execution_time and (time.time() - start_time) > max_execution_time:
            yield SSEEvent(event="timeout", data={"iteration": iteration})
            break
        
        # Get tools
        tools = tool_registry.get_openai_tools(self.get_tool_names())
        
        # Step 1: Call LLM (with tracing in method)
        result = await self._call_llm_streaming(messages, tools, llm_config, callbacks)
        yield from result.events
        
        # Step 2: Check if done
        if not result.tool_calls:
            messages.append({"role": "assistant", "content": result.content})
            yield SSEEvent(event="done", data={})
            return
        
        # Step 3: Execute tools (with error handling in method)
        messages.append({"role": "assistant", "content": result.content, "tool_calls": result.tool_calls})
        
        tool_result = await self._execute_tools_streaming(result.tool_calls, context, callbacks)
        yield from tool_result.events
        messages.extend(tool_result.messages)
        
        # Step 4: Optional thinking indicator
        if callbacks:
            yield from await callbacks.on_thinking()
    
    # Max iterations reached
    yield SSEEvent(event="max_iterations", data={"iterations": max_iterations})
```

Much cleaner! All tracing, timing, and complex event handling moved to helper methods.

## Conclusion

Our current implementation is solid with a clean ReAct pattern. The main improvements would be:

1. **Reduce complexity** - Extract tracing/timing to decorators/helpers
2. **Better error handling** - Timeouts, retries, graceful degradation  
3. **Type safety** - Replace magic strings with proper types
4. **Simpler interfaces** - Consolidate callbacks

These changes would make the core loop easier to understand and maintain, similar to LangChain's philosophy of clean abstractions.

