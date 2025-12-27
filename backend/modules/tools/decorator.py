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
    requires_auth: bool = False,
    hidden_from_ui: bool = False,  # Mark tools that shouldn't appear in chat UI
    api_docs_only: bool = False  # Tool docs saved to filesystem instead of sent to LLM
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
            context: AgentContext,  # Hidden from LLM - injected by executor
            include_closed: bool = False  # Visible to LLM
        ) -> Dict[str, Any]:
            # 'user_description' param is auto-injected into schema but NOT in function signature
            # LLM provides it when calling: get_portfolio(user_description="...", include_closed=True)
            # Executor strips it before calling this function
            pass
    
    Requirements:
    - Function must accept keyword-only arguments (use * separator)
    - Function must have a 'context' parameter of type AgentContext
    - Function should NOT have a 'user_description' parameter (it's auto-injected into schema)
    - The 'context' parameter is EXCLUDED from OpenAI schema
    - All other parameters will be exposed to the LLM in the tool schema
    
    Special Parameters:
    - 'context': AgentContext - Hidden from LLM, injected by executor, contains user_id, chat_id
    - 'user_description': str - Auto-injected into ALL tool schemas for LLM to provide user-friendly text
                               Extracted by executor before calling tool function (never reaches tool)
    
    Args:
        description: Description of what the tool does (for LLM documentation)
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
            # Skip special hidden parameters
            if param_name in ('context', 'user_description'):
                continue  # Skip context and user_description - handled by executor
            
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
        
        # Automatically inject 'user_description' parameter for most tools
        # BUT exclude it for message_notify_user and message_ask_user (they ARE the description!)
        if tool_name not in ('message_notify_user', 'message_ask_user'):
            properties["user_description"] = {
                "type": "string",
                "description": "User-friendly description of what this specific tool call is doing (will be shown to the user)"
            }
            # Make user_description required for better UI display
            required.append('user_description')
        
        # Build OpenAI parameters schema
        parameters_schema = {
            "type": "object",
            "properties": properties,
            "required": required
        }
        
        # Check if function is async (includes both regular async and async generators)
        is_async = inspect.iscoroutinefunction(func) or inspect.isasyncgenfunction(func)
        
        # Create tool
        tool_obj = Tool(
            name=tool_name,
            description=description,
            handler=func,
            parameters_schema=parameters_schema,
            is_async=is_async,
            category=category,
            requires_auth=requires_auth,
            hidden_from_ui=hidden_from_ui,
            api_docs_only=api_docs_only
        )
        
        # Attach tool to function for registry
        func._tool = tool_obj
        
        # AUTO-REGISTER: Register tool immediately when decorator is applied
        # This eliminates the need for manual registration in definitions.py
        from .registry import tool_registry
        tool_registry.register(tool_obj)
        
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


def _clean_schema_for_claude(schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove fields that are not compatible with Anthropic's JSON Schema requirements.
    
    Anthropic requires strict JSON Schema draft 2020-12 compliance, which means:
    - No $schema, title, $defs, additionalProperties (unless explicitly needed)
    - Clean, minimal schema structure
    - Simplified Optional handling (anyOf -> simpler form)
    
    Args:
        schema: Schema to clean
    
    Returns:
        Cleaned schema
    """
    if not isinstance(schema, dict):
        return schema
    
    # Fields to remove for Claude compatibility
    fields_to_remove = ["$schema", "title", "additionalProperties", "$defs"]
    
    cleaned = {}
    for key, value in schema.items():
        if key in fields_to_remove:
            continue
        
        # Simplify anyOf for Optional fields
        # Pydantic generates {"anyOf": [{"type": "X"}, {"type": "null"}]} for Optional[X]
        # Claude prefers simpler schemas, so we can mark as not required instead
        if key == "anyOf" and isinstance(value, list):
            # Check if this is an Optional pattern (has null type)
            has_null = any(isinstance(item, dict) and item.get("type") == "null" for item in value)
            non_null_schemas = [item for item in value if not (isinstance(item, dict) and item.get("type") == "null")]
            
            if has_null and len(non_null_schemas) == 1:
                # This is Optional[X], just use X's schema
                # The field being optional is handled by 'required' list at parent level
                return _clean_schema_for_claude(non_null_schemas[0])
        
        # Recursively clean nested objects
        if isinstance(value, dict):
            cleaned[key] = _clean_schema_for_claude(value)
        elif isinstance(value, list):
            cleaned[key] = [_clean_schema_for_claude(item) if isinstance(item, dict) else item for item in value]
        else:
            cleaned[key] = value
    
    return cleaned


def _resolve_refs(schema: Dict[str, Any], defs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively resolve $ref references in a JSON schema.
    
    Anthropic/Claude requires schemas to not use $ref/$defs, so we inline all references.
    
    Args:
        schema: The schema object to resolve
        defs: The $defs dictionary containing definitions
    
    Returns:
        Schema with all references resolved inline
    """
    if isinstance(schema, dict):
        # Check if this is a reference
        if "$ref" in schema:
            ref_path = schema["$ref"]
            # Extract definition name from ref (e.g., "#/$defs/DataSourceInput" -> "DataSourceInput")
            if ref_path.startswith("#/$defs/"):
                def_name = ref_path.replace("#/$defs/", "")
                if def_name in defs:
                    # Recursively resolve the referenced definition
                    resolved = _resolve_refs(defs[def_name].copy(), defs)
                    # Clean the resolved schema
                    return _clean_schema_for_claude(resolved)
            return schema
        
        # Recursively resolve all values in the dict
        return {key: _resolve_refs(value, defs) for key, value in schema.items()}
    
    elif isinstance(schema, list):
        # Recursively resolve all items in the list
        return [_resolve_refs(item, defs) for item in schema]
    
    else:
        # Primitive value, return as-is
        return schema


def _get_pydantic_schema(annotation) -> Optional[Dict[str, Any]]:
    """
    Get JSON schema from Pydantic model (best practice for complex types)
    Returns None if not a Pydantic model
    
    Handles nested models by resolving $ref references inline for Claude/Anthropic compatibility.
    """
    try:
        from pydantic import BaseModel
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            # Use Pydantic's built-in schema generation
            schema = annotation.model_json_schema()
            
            # Check if schema has $defs (nested model definitions)
            defs = schema.get("$defs", {})
            
            if defs:
                # Resolve all $ref references inline to make schema Claude-compatible
                resolved_schema = _resolve_refs(schema, defs)
                # Clean the schema to remove incompatible fields
                cleaned_schema = _clean_schema_for_claude(resolved_schema)
                result = {
                    "type": "object",
                    "properties": cleaned_schema.get("properties", {}),
                    "required": cleaned_schema.get("required", [])
                }
                # Only add description if it's not empty
                if cleaned_schema.get("description"):
                    result["description"] = cleaned_schema["description"]
                logger.debug(f"Generated Pydantic schema for {annotation.__name__}: {result}")
                return result
            else:
                # No nested models, simple schema - still clean it
                cleaned_schema = _clean_schema_for_claude(schema)
                result = {
                    "type": "object",
                    "properties": cleaned_schema.get("properties", {}),
                    "required": cleaned_schema.get("required", [])
                }
                # Only add description if it's not empty
                if cleaned_schema.get("description"):
                    result["description"] = cleaned_schema["description"]
                logger.debug(f"Generated Pydantic schema for {annotation.__name__}: {result}")
                return result
    except Exception as e:
        logger.error(f"Error generating Pydantic schema: {e}", exc_info=True)
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

