# Agent Architecture - Base Class Pattern

## Overview

We've refactored the agent system to use a **base agent class** that provides reusable LLM interaction logic. This eliminates code duplication and makes it easy to create specialized agents.

## Class Hierarchy

```
BaseAgent (abstract)
├── ChatAgent (main agent - streaming to users)
└── PlottingAgent (specialized - creates charts)
```

## BaseAgent

Located in `modules/agent/base_agent.py`

### Abstract Methods (Must Implement)

```python
def get_system_prompt(self, **kwargs) -> str:
    """Return the system prompt for this agent"""
    pass

def get_tool_registry(self) -> ToolRegistry:
    """Return the tool registry with available tools"""
    pass

def get_model(self) -> str:
    """Return the LLM model name (e.g., 'gpt-4o-mini')"""
    pass
```

### Provided Methods

#### 1. `run_tool_loop()` - Non-Streaming
For agents that don't need to stream to users:

```python
result = await agent.run_tool_loop(
    initial_messages=messages,
    session_id=session_id,
    max_iterations=10,
    temperature=0.7
)
# Returns: {success, content, tool_results, iterations}
```

#### 2. `run_tool_loop_streaming()` - Streaming
For agents that stream responses to users:

```python
async for event in agent.run_tool_loop_streaming(
    initial_messages=messages,
    session_id=session_id,
    on_content_delta=handle_content,
    on_tool_call_start=handle_tool_start,
    on_tool_call_complete=handle_tool_complete,
    on_thinking=handle_thinking
):
    yield event
```

Callbacks allow customizing SSE events.

#### 3. `build_messages()`
Helper for building message lists:

```python
messages = agent.build_messages(
    user_message="Create a chart",
    chat_history=[...],
    **kwargs  # Passed to get_system_prompt()
)
```

#### 4. `get_new_messages()`
Get messages added during last interaction (for DB storage):

```python
new_messages = agent.get_new_messages()
```

## PlottingAgent - Example Usage

The `PlottingAgent` is a clean example of using `BaseAgent`:

```python
class PlottingAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self._tool_registry = ToolRegistry()
        self._tool_registry.register_function(create_chart)
    
    def get_system_prompt(self, **kwargs) -> str:
        return "You are a plotting expert..."
    
    def get_tool_registry(self) -> ToolRegistry:
        return self._tool_registry
    
    def get_model(self) -> str:
        return "gpt-4o-mini"
    
    async def create_plot(self, objective, data, session_id):
        messages = self.build_messages(
            f"Objective: {objective}\nData: {data}"
        )
        result = await self.run_tool_loop(
            messages, 
            session_id, 
            max_iterations=3
        )
        return result["tool_results"][0]["result"]
```

**Key Benefits:**
- ✅ Only ~50 lines of code (vs ~150 before)
- ✅ No LLM interaction boilerplate
- ✅ Automatic tool execution
- ✅ Built-in error handling

## ChatAgent Status

The main `ChatAgent` **can be refactored** to inherit from `BaseAgent`, but it has some specific requirements:

### Current ChatAgent-Specific Logic
1. **Auth Status**: Checks SnapTrade connection, adds to prompt
2. **Tool Call Tracking**: Stores tool execution info for resource creation
3. **Portfolio Truncation**: Special handling for large portfolio data
4. **Message History Cleanup**: Removes incomplete tool calls
5. **SSE Events**: Custom event types for frontend

### Refactoring Options

#### Option 1: Minimal Refactor (Keep Current)
- Keep ChatAgent as-is
- Only use BaseAgent for new specialized agents
- **Pros**: No risk, works perfectly
- **Cons**: Some code duplication

#### Option 2: Full Refactor (Use BaseAgent)
- ChatAgent inherits from BaseAgent
- Use `run_tool_loop_streaming()` with callbacks
- Move portfolio-specific logic to callbacks
- **Pros**: Maximum code reuse
- **Cons**: Larger refactor, more testing needed

#### Option 3: Hybrid (Recommended)
- Keep ChatAgent independent for now
- Use BaseAgent for all new agents
- Gradually extract common patterns
- **Pros**: Best of both worlds
- **Cons**: Temporary duplication

## Creating New Specialized Agents

Use this pattern for any new agent:

```python
class DataAnalysisAgent(BaseAgent):
    """Analyzes datasets and generates insights"""
    
    def __init__(self):
        super().__init__()
        self._tool_registry = ToolRegistry()
        # Register analysis tools
        self._tool_registry.register_function(analyze_trends)
        self._tool_registry.register_function(find_correlations)
        self._tool_registry.register_function(detect_anomalies)
    
    def get_system_prompt(self, **kwargs) -> str:
        return """You are a data analysis expert.
        Analyze datasets and provide statistical insights.
        Use available tools to compute trends, correlations, and anomalies."""
    
    def get_tool_registry(self) -> ToolRegistry:
        return self._tool_registry
    
    def get_model(self) -> str:
        return "gpt-4"  # Use better model for analysis
    
    async def analyze(self, data, objective, session_id):
        """Public API for running analysis"""
        messages = self.build_messages(
            f"Analyze this data: {objective}\n\n{data}"
        )
        result = await self.run_tool_loop(
            messages,
            session_id,
            max_iterations=5,
            temperature=0.3  # Lower for consistent analysis
        )
        return result
```

## Agent Delegation Pattern

The plotting system demonstrates the **delegation pattern**:

```
User → ChatAgent → create_plot tool → PlottingAgent → create_chart tool → Result
```

**Benefits:**
1. **Separation of Concerns**: Each agent has single responsibility
2. **Specialized Expertise**: Plotting agent knows charts, main agent doesn't need to
3. **Independent Tool Registries**: No tool namespace conflicts
4. **Composability**: Agents can call other agents
5. **Testability**: Each agent tested independently

## Future Agents

Consider creating specialized agents for:

- **ResearchAgent**: Web search, article summarization, fact-checking
- **PortfolioAnalysisAgent**: Deep portfolio analytics, risk analysis
- **TradingAgent**: Order execution, strategy backtesting
- **ReportingAgent**: Generate PDF/Excel reports
- **AlertAgent**: Monitor conditions, send notifications

## Best Practices

### 1. Keep Agents Focused
Each agent should do ONE thing well.

### 2. Use Appropriate Models
- **gpt-4o-mini**: Fast, cheap (plotting, simple tasks)
- **gpt-4o**: Balanced (main chat)
- **gpt-4**: Best quality (complex analysis)

### 3. Limit Tool Calls
Set `max_iterations` based on task complexity:
- Simple: 2-3 iterations
- Medium: 5 iterations
- Complex: 10 iterations

### 4. Temperature Settings
- **0.1-0.3**: Deterministic tasks (plotting, data processing)
- **0.7-0.9**: Creative tasks (content generation)
- **1.0**: Default (chat)

### 5. Custom System Prompts
Make prompts specific and actionable:
- ✅ "You are a plotting expert. Create visualizations using create_chart tool."
- ❌ "You are helpful."

### 6. Error Handling
Agents automatically handle errors, but you can add custom logic:

```python
result = await agent.run_tool_loop(...)
if not result["success"]:
    # Handle failure
    return fallback_response
```

## Testing Agents

```python
# Test plotting agent
from modules.agent.plotting_agent import plotting_agent

result = await plotting_agent.create_plot(
    objective="Line chart with trendline",
    data={"x": [1,2,3], "y": [10,20,15]},
    session_id="test"
)

assert result["success"]
assert "plotly_json" in result
```

## Migration Guide

To refactor ChatAgent to use BaseAgent:

1. Make ChatAgent inherit from BaseAgent
2. Implement abstract methods
3. Replace streaming loop with `run_tool_loop_streaming()`
4. Move SSE event generation to callbacks
5. Test thoroughly with existing features

This is **optional** - current ChatAgent works great!

## Summary

✅ **BaseAgent** provides reusable agent infrastructure
✅ **PlottingAgent** demonstrates clean usage
✅ **ChatAgent** can stay independent (works perfectly)
✅ **Future agents** get 80% of code for free
✅ **Delegation pattern** enables specialized sub-agents

The architecture is flexible - use BaseAgent for new agents, keep ChatAgent as-is unless refactoring provides clear benefits.

