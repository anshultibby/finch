"""
Tool decorator for converting functions into LLM-callable tools
"""
import inspect
from typing import Callable, Optional, List, Any, Dict, get_type_hints, get_origin, get_args, AsyncGenerator, Union
from functools import wraps

from .models import Tool
from modules.agent.context import AgentContext
from .responses import ToolResponse, ToolSuccess, ToolError
from models.sse import SSEEvent
from utils.logger import get_logger

logger = get_logger(__name__)


def tool(
    description: str,
    name: Optional[str] = None,
    category: Optional[str] = None,
    requires_auth: bool = False
):
    """
    Decorator to convert a function into an LLM-callable tool.
    
    Usage:
        @tool(
            description="Fetch user's portfolio holdings",
            category="portfolio",
            requires_auth=True
        )
        async def get_portfolio(
            *,  # Force keyword args
            context: AgentContext,  # NOT visible to LLM
            include_closed: bool = False  # Visible to LLM
        ) -> Dict[str, Any]:
            # Implementation
            pass
    
    Requirements:
    - Function must accept keyword-only arguments (use * separator)
    - Function must have a 'context' parameter of type AgentContext
    - Function must return Dict[str, Any]
    - The 'context' parameter is EXCLUDED from OpenAI schema (hidden from LLM)
    - All other parameters will be exposed to the LLM in the tool schema
    
    Security Note:
    - The 'context' parameter contains user_id, chat_id, and other secure data
    - It is passed by the tool executor, NOT by the LLM
    - It never appears in the OpenAI tool schema
    
    Args:
        description: Description of what the tool does (for LLM)
        name: Tool name (defaults to function name if not provided)
        category: Optional category for grouping tools
        requires_auth: Whether tool requires user authentication
    """
    def decorator(func: Callable) -> Callable:
        # Use function name if name not provided
        tool_name = name or func.__name__
        # Validate function signature
        sig = inspect.signature(func)
        
        # Check that function has keyword-only args
        has_kwonly = any(
            p.kind == inspect.Parameter.KEYWORD_ONLY 
            for p in sig.parameters.values()
        )
        if not has_kwonly:
            raise ValueError(
                f"Tool function '{tool_name}' must use keyword-only arguments. "
                "Add * before parameters: def func(*, context, param1, param2)"
            )
        
        # Check for context parameter
        if 'context' not in sig.parameters:
            raise ValueError(
                f"Tool function '{tool_name}' must have a 'context' parameter of type AgentContext"
            )
        
        # Build OpenAI parameters schema directly
        # SECURITY: 'context' parameter is NEVER exposed to LLM
        properties = {}
        required = []
        
        for param_name, param in sig.parameters.items():
            if param_name == 'context':
                continue  # Skip context - it's passed by code, not LLM
            
            # Check if parameter is a Pydantic model (best practice)
            param_schema = _get_pydantic_schema(param.annotation)
            
            if param_schema is None:
                # Build parameter schema from type hints
                param_schema = {
                    "type": _python_type_to_json_type(param.annotation),
                    "description": _extract_param_description(func, param_name)
                }
                
                # Handle List types
                if _is_list_type(param.annotation):
                    param_schema["type"] = "array"
                    item_type = _get_list_item_type(param.annotation)
                    param_schema["items"] = {"type": item_type}
            else:
                # Use Pydantic-generated schema
                # Add description from docstring if not in schema
                if "description" not in param_schema:
                    param_schema["description"] = _extract_param_description(func, param_name)
            
            # Add to properties
            properties[param_name] = param_schema
            
            # Check if required (no default value)
            if param.default == inspect.Parameter.empty:
                required.append(param_name)
        
        # Build OpenAI parameters schema
        parameters_schema = {
            "type": "object",
            "properties": properties,
            "required": required
        }
        
        # Check if function is async
        is_async = inspect.iscoroutinefunction(func)
        
        # Create tool
        tool_obj = Tool(
            name=tool_name,
            description=description,
            handler=func,
            parameters_schema=parameters_schema,
            is_async=is_async,
            category=category,
            requires_auth=requires_auth
        )
        
        # Attach tool to function for registry
        func._tool = tool_obj
        
        # Check if function is async generator (yields events)
        is_async_gen = inspect.isasyncgenfunction(func)
        
        # Create appropriate wrapper based on function type
        if is_async_gen:
            # Async generator wrapper - yields from the underlying generator
            @wraps(func)
            async def async_gen_wrapper(*args, **kwargs):
                # Call the async generator function and yield all items
                async for item in func(*args, **kwargs):
                    yield item
            
            wrapper = async_gen_wrapper
        elif is_async:
            # Regular async function wrapper
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                result = await func(*args, **kwargs)
                # Enforce ToolResponse format
                return _ensure_tool_response(result, tool_name)
            
            wrapper = async_wrapper
        else:
            # Sync function wrapper
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                result = func(*args, **kwargs)
                # Sync tools don't support yielding (must be async)
                return _ensure_tool_response(result, tool_name)
            
            wrapper = sync_wrapper
        wrapper._tool = tool_obj
        wrapper._is_async_gen = is_async_gen  # Mark if it's a generator
        
        return wrapper
    
    return decorator


def _python_type_to_json_type(annotation) -> str:
    """Convert Python type annotation to JSON schema type"""
    if annotation == inspect.Parameter.empty or annotation is None:
        return "string"
    
    # Check if it's a Pydantic model
    try:
        from pydantic import BaseModel
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            return "object"
    except:
        pass
    
    # Handle typing module types
    origin = get_origin(annotation)
    
    if origin is list:
        return "array"
    if origin is dict:
        return "object"
    
    # Handle basic types
    type_map = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object"
    }
    
    return type_map.get(annotation, "string")


def _is_list_type(annotation) -> bool:
    """Check if annotation is a List type"""
    origin = get_origin(annotation)
    return origin is list


def _get_list_item_type(annotation) -> str:
    """Get the item type from a List annotation"""
    args = get_args(annotation)
    if args:
        return _python_type_to_json_type(args[0])
    return "string"


def _get_pydantic_schema(annotation) -> Optional[Dict[str, Any]]:
    """
    Get JSON schema from Pydantic model (best practice for complex types)
    Returns None if not a Pydantic model
    """
    try:
        from pydantic import BaseModel
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            # Use Pydantic's built-in schema generation (OpenAI-compatible)
            schema = annotation.model_json_schema()
            # Return simplified schema for OpenAI (without title, etc.)
            return {
                "type": "object",
                "properties": schema.get("properties", {}),
                "required": schema.get("required", []),
                "description": schema.get("description", "")
            }
    except:
        pass
    return None


def _extract_param_description(func: Callable, param_name: str) -> str:
    """
    Extract parameter description from function docstring.
    Looks for Args section with parameter descriptions.
    """
    docstring = inspect.getdoc(func)
    if not docstring:
        return f"Parameter: {param_name}"
    
    # Look for Args section and param_name
    lines = docstring.split('\n')
    in_args_section = False
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Check if we're entering Args section
        if stripped.lower().startswith('args:'):
            in_args_section = True
            continue
        
        # Check if we're leaving Args section
        if in_args_section and stripped.endswith(':') and not stripped.startswith(param_name):
            break
        
        # Look for parameter in Args section
        if in_args_section and param_name in stripped and ':' in stripped:
            # Extract description after colon
            parts = stripped.split(':', 1)
            if len(parts) > 1:
                return parts[1].strip()
    
    return f"Parameter: {param_name}"


def _ensure_tool_response(result: Any, tool_name: str) -> ToolResponse:
    """
    Ensure tool returns a ToolResponse (enforced format).
    
    If not, wrap it or raise error.
    """
    # Already a ToolResponse - good!
    if isinstance(result, ToolResponse):
        return result
    
    # Legacy dict format - auto-convert with warning
    if isinstance(result, dict):
        logger.warning(
            f"Tool '{tool_name}' returned dict instead of ToolResponse. "
            "Please update tool to use ToolSuccess or ToolError."
        )
        
        # Try to convert to ToolResponse
        success = result.get("success", True)
        if success:
            return ToolSuccess(
                data=result.get("data"),
                message=result.get("message")
            )
        else:
            return ToolError(
                error=result.get("error", "Unknown error"),
                message=result.get("message"),
                data=result.get("data")
            )
    
    # Invalid format - return error
    logger.error(
        f"Tool '{tool_name}' returned invalid type: {type(result).__name__}. "
        "Tools must return ToolResponse (ToolSuccess or ToolError)."
    )
    return ToolError(
        error=f"Tool returned invalid type: {type(result).__name__}",
        message="Internal tool error - invalid response format"
    )

