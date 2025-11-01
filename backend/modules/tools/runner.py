"""
Tool Runner - Handles execution of tools

Separates execution logic from registry (storage) and agents (orchestration)
"""
from typing import Dict, Any, Optional
import traceback
import inspect

from pydantic import BaseModel
from .models import ToolContext
from .registry import tool_registry
from .stream_handler import ToolStreamHandler


class ToolRunner:
    """
    Executes tools with proper error handling and context management.
    
    Responsibilities:
    - Execute tools from the registry
    - Handle errors gracefully
    - Manage context (session_id, user_id, etc.)
    - Log execution for debugging
    """
    
    def __init__(self, registry=None):
        """
        Initialize tool runner
        
        Args:
            registry: ToolRegistry to use (defaults to global registry)
        """
        self.registry = registry or tool_registry
    
    async def execute(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        context: Optional[ToolContext] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        stream_handler: Optional[ToolStreamHandler] = None,
        resource_manager: Optional[Any] = None,
        chat_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a tool with given arguments
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Arguments from LLM (keyword args for the function)
            context: Pre-built context (if provided, ignores other parameters)
            session_id: User session ID (if context not provided)
            user_id: User ID (if context not provided)
            stream_handler: Optional stream handler for tool progress updates
            resource_manager: Optional resource manager for accessing/registering resources
            chat_id: Optional chat ID for resource context
        
        Returns:
            Tool execution result with standard format:
            {
                "success": bool,
                "data": Any,  # Tool-specific result
                "message": str,  # Optional message
                "error": str  # Error details if failed
            }
        """
        # Build context if not provided
        if context is None:
            context = ToolContext(
                session_id=session_id,
                user_id=user_id,
                stream_handler=stream_handler,
                resource_manager=resource_manager,
                chat_id=chat_id
            )
        else:
            # Update context with any provided values that aren't already set
            if stream_handler and not context.stream_handler:
                context.stream_handler = stream_handler
            if resource_manager and not context.resource_manager:
                context.resource_manager = resource_manager
            if chat_id and not context.chat_id:
                context.chat_id = chat_id
            if user_id and not context.user_id:
                context.user_id = user_id
        
        # Get tool from registry
        tool = self.registry.get_tool(tool_name)
        if not tool:
            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}",
                "message": f"Tool '{tool_name}' not found in registry"
            }
        
        try:
            print(f"🔧 Executing tool: {tool_name}", flush=True)
            
            # Inspect function signature to detect Pydantic model parameters
            sig = inspect.signature(tool.handler)
            kwargs = {"context": context}
            
            # Check if any parameter (excluding 'context') is a Pydantic model
            pydantic_param = None
            for param_name, param in sig.parameters.items():
                if param_name == 'context':
                    continue
                
                # Check if this parameter is a Pydantic BaseModel
                param_annotation = param.annotation
                try:
                    if (isinstance(param_annotation, type) and 
                        issubclass(param_annotation, BaseModel)):
                        # Found a Pydantic model parameter
                        pydantic_param = (param_name, param_annotation)
                        break
                except TypeError:
                    # param_annotation is not a class (e.g., it's a typing construct)
                    continue
            
            # If we found a Pydantic parameter, construct it from arguments
            if pydantic_param:
                param_name, param_class = pydantic_param
                print(f"🔍 Detected Pydantic parameter: {param_name} of type {param_class.__name__}", flush=True)
                
                # Check if arguments are already wrapped in the parameter name
                if param_name in arguments and isinstance(arguments[param_name], dict):
                    # Already wrapped: {"params": {...}}
                    print(f"📦 Arguments already wrapped in '{param_name}'", flush=True)
                    kwargs[param_name] = param_class(**arguments[param_name])
                elif param_name in arguments:
                    # Already wrapped but might already be a model instance
                    print(f"📦 Found existing '{param_name}' in arguments", flush=True)
                    kwargs[param_name] = arguments[param_name]
                else:
                    # Not wrapped, assume all arguments are for the model: {"data_series": ..., "plot_type": ...}
                    print(f"📦 Arguments flattened, constructing {param_class.__name__} from: {list(arguments.keys())}", flush=True)
                    kwargs[param_name] = param_class(**arguments)
            else:
                # No Pydantic models, just unpack arguments normally
                kwargs.update(arguments)
            
            # Execute tool (async or sync)
            if tool.is_async:
                result = await tool.handler(**kwargs)
            else:
                result = tool.handler(**kwargs)
            
            # Ensure result is a dict
            if not isinstance(result, dict):
                print(f"⚠️ Tool {tool_name} returned non-dict: {type(result)}", flush=True)
                result = {"success": True, "data": result}
            
            # Add success flag if not present
            if "success" not in result:
                result["success"] = True
            
            if result.get("success"):
                print(f"✅ Tool {tool_name} completed successfully", flush=True)
            else:
                print(f"⚠️ Tool {tool_name} returned success=False: {result.get('message', 'No message')}", flush=True)
            
            return result
        
        except Exception as e:
            error_msg = str(e)
            error_trace = traceback.format_exc()
            
            print(f"❌ Error executing tool {tool_name}: {error_msg}", flush=True)
            print(f"❌ Traceback:\n{error_trace}", flush=True)
            
            return {
                "success": False,
                "error": error_msg,
                "message": f"Tool execution failed: {error_msg}",
                "traceback": error_trace
            }
    
    async def execute_multiple(
        self,
        tool_calls: list[Dict[str, Any]],
        context: Optional[ToolContext] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> list[Dict[str, Any]]:
        """
        Execute multiple tool calls in sequence
        
        Args:
            tool_calls: List of tool calls with format:
                [
                    {"tool_name": "get_portfolio", "arguments": {...}},
                    {"tool_name": "create_chart", "arguments": {...}}
                ]
            context: Pre-built context
            session_id: User session ID
            user_id: User ID
        
        Returns:
            List of results in same order as tool_calls
        """
        results = []
        
        for tool_call in tool_calls:
            result = await self.execute(
                tool_name=tool_call["tool_name"],
                arguments=tool_call.get("arguments", {}),
                context=context,
                session_id=session_id,
                user_id=user_id
            )
            results.append(result)
        
        return results
    
    def validate_arguments(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """
        Validate arguments against tool's parameter schema
        
        Args:
            tool_name: Name of the tool
            arguments: Arguments to validate
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        tool = self.registry.get_tool(tool_name)
        if not tool:
            return False, f"Tool '{tool_name}' not found"
        
        schema = tool.parameters_schema
        required_params = schema.get("required", [])
        
        # Check required parameters
        missing = [p for p in required_params if p not in arguments]
        if missing:
            return False, f"Missing required parameters: {', '.join(missing)}"
        
        # Could add type validation here
        
        return True, None


# Global tool runner instance
tool_runner = ToolRunner()

