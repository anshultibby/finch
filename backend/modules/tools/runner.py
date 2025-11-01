"""
Tool Runner - Handles execution of tools

Separates execution logic from registry (storage) and agents (orchestration)
"""
from typing import Dict, Any, Optional
import traceback

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
        stream_handler: Optional[ToolStreamHandler] = None
    ) -> Dict[str, Any]:
        """
        Execute a tool with given arguments
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Arguments from LLM (keyword args for the function)
            context: Pre-built context (if provided, ignores session_id/user_id/stream_handler)
            session_id: User session ID (if context not provided)
            user_id: User ID (if context not provided)
            stream_handler: Optional stream handler for tool progress updates
        
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
                stream_handler=stream_handler
            )
        elif stream_handler and not context.stream_handler:
            # Add stream_handler to existing context if provided
            context.stream_handler = stream_handler
        
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
            
            # Merge context into arguments
            kwargs = {"context": context, **arguments}
            
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

