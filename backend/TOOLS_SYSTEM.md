# Tool System Documentation

## Overview

The tool system provides a clean, decorator-based approach to define LLM-callable tools. It automatically generates OpenAI-compatible function calling schemas and manages tool registration and execution.

## Architecture

### Components

1. **`@tool` Decorator** (`modules/tools/decorator.py`)
   - Converts Python functions into LLM-callable tools
   - Auto-generates OpenAI function calling schemas
   - Extracts parameter info from type hints and docstrings

2. **Tool Registry** (`modules/tools/registry.py`)
   - Central registry for all tools
   - Manages tool lookup and execution
   - Generates OpenAI schemas on demand

3. **Tool Definitions** (`modules/tool_definitions.py`)
   - Single file containing all tool definitions
   - Tools are thin wrappers that call business logic modules

4. **Tool Context** (`modules/tools/models.py`)
   - Secure context passed to tools (NOT visible to LLM)
   - Contains `session_id`, `user_id`, etc.

## Defining a Tool

### Basic Example

```python
from modules.tools import tool, ToolContext
from typing import Dict, Any

@tool(
    description="Get weather for a city",
    category="weather"
)
async def get_weather(
    *,
    context: ToolContext,  # Hidden from LLM
    city: str,             # Visible to LLM
    units: str = "metric"  # Optional param with default
) -> Dict[str, Any]:
    """
    Get current weather
    
    Args:
        city: City name
        units: Temperature units (metric or imperial)
    """
    # Implementation...
    return {"success": True, "temp": 72}
```

### Key Features

1. **Auto-name from function**: Tool name is `get_weather` (from function name)
2. **Context parameter**: Always required, never exposed to LLM
3. **Type hints**: Auto-converted to JSON schema types
4. **Docstring parsing**: Extracts parameter descriptions
5. **OpenAI schema**: Auto-generated in correct format

## Best Practices

### 1. Use Type Hints

```python
@tool(description="...")
async def my_tool(
    *,
    context: ToolContext,
    name: str,              # → "type": "string"
    age: int,               # → "type": "integer"
    tags: List[str],        # → "type": "array", "items": {"type": "string"}
    data: Optional[dict]    # → "type": "object" (optional)
) -> Dict[str, Any]:
    ...
```

### 2. Use Pydantic for Complex Types

For nested objects, use Pydantic models (industry best practice):

```python
from pydantic import BaseModel

class UserPreferences(BaseModel):
    theme: str
    notifications: bool
    language: str = "en"

@tool(description="Update user preferences")
async def update_preferences(
    *,
    context: ToolContext,
    preferences: UserPreferences  # Auto-converted using Pydantic's schema
) -> Dict[str, Any]:
    ...
```

The decorator automatically uses Pydantic's `.model_json_schema()` for OpenAI-compatible schemas.

### 3. Document Parameters

Use Google-style docstrings:

```python
@tool(description="...")
async def my_tool(
    *,
    context: ToolContext,
    ticker: str,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Tool description
    
    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL')
        limit: Maximum number of results (default 10)
    """
    ...
```

### 4. Always Use Keyword-Only Args

Force keyword args with `*`:

```python
def my_tool(*, context: ToolContext, param1: str):  # ✅ Good
    ...

def my_tool(context: ToolContext, param1: str):     # ❌ Bad
    ...
```

## Tool Registration

Tools are auto-registered on import:

```python
# In tool_definitions.py
@tool(description="...")
def my_tool(...):
    ...

# Register all tools
def register_all_tools():
    tool_registry.register_function(my_tool)
    # ... register others

# Auto-register on import
register_all_tools()
```

## Using the Registry

### Get All Tools

```python
from modules.tools import tool_registry

# Get all OpenAI schemas
schemas = tool_registry.get_all_schemas()

# Pass to LiteLLM
response = await acompletion(
    model="gpt-4",
    messages=messages,
    tools=schemas  # ← Auto-generated schemas
)
```

### Filter Tools

```python
# Get tools by category
portfolio_tools = tool_registry.list_tools(category="portfolio")

# Get tools requiring auth
auth_tools = tool_registry.list_tools(requires_auth=True)

# Get filtered schemas
schemas = tool_registry.get_openai_schemas(category="portfolio")
```

### Execute Tools

```python
from modules.tools import ToolContext, tool_registry

# Create context (secure data)
context = ToolContext(
    session_id="user_session_123",
    user_id="user_456"
)

# Execute tool
result = await tool_registry.execute_tool(
    tool_name="get_portfolio",
    arguments={"include_closed": False},  # From LLM
    context=context                        # From code
)
```

## Security

### Context vs Arguments

- **Arguments**: Passed by LLM, visible in OpenAI schema
- **Context**: Passed by code, NEVER visible to LLM

```python
@tool(description="...")
async def sensitive_tool(
    *,
    context: ToolContext,    # ← session_id, API keys (SECURE)
    ticker: str              # ← from LLM (public)
) -> Dict[str, Any]:
    # Access secure data from context
    session_id = context.session_id
    
    # Use public argument from LLM
    return fetch_data(ticker, session_id=session_id)
```

## Generated Schema Example

For this tool:

```python
@tool(description="Get stock price")
async def get_stock_price(
    *,
    context: ToolContext,
    ticker: str,
    currency: str = "USD"
) -> Dict[str, Any]:
    """
    Args:
        ticker: Stock ticker symbol
        currency: Currency code
    """
    ...
```

Generated OpenAI schema:

```json
{
  "type": "function",
  "function": {
    "name": "get_stock_price",
    "description": "Get stock price",
    "parameters": {
      "type": "object",
      "properties": {
        "ticker": {
          "type": "string",
          "description": "Stock ticker symbol"
        },
        "currency": {
          "type": "string",
          "description": "Currency code"
        }
      },
      "required": ["ticker"]
    }
  }
}
```

Note: `context` is NOT in the schema!

## Adding New Tools

1. **Define tool in `tool_definitions.py`**:

```python
@tool(
    description="Your tool description",
    category="your_category"
)
async def your_tool(
    *,
    context: ToolContext,
    param1: str
) -> Dict[str, Any]:
    """
    Args:
        param1: Parameter description
    """
    return await your_module.do_something(param1)
```

2. **Register in `register_all_tools()`**:

```python
def register_all_tools():
    # ... existing registrations
    tool_registry.register_function(your_tool)
```

That's it! The tool is now available to the LLM.

## Migration from Old System

### Before (Old):

```python
# Separate tool definition
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_portfolio",
            "description": "...",
            "parameters": { ... }
        }
    }
]

# Separate execution logic
if function_name == "get_portfolio":
    return snaptrade_tools.get_portfolio(session_id)
```

### After (New):

```python
@tool(description="...")
def get_portfolio(*, context: ToolContext) -> Dict[str, Any]:
    return snaptrade_tools.get_portfolio(session_id=context.session_id)
```

Much cleaner! Schema generation and execution are automatic.

