"""
Tool registry for managing and executing tools
"""
from typing import Dict, List, Optional, Any, Callable

from .models import Tool, ToolContext


class ToolRegistry:
    """
    Central registry for all tools.
    Manages tool registration, lookup, and execution.
    """
    
    def __init__(self):
        self._tools: Dict[str, Tool] = {}
    
    def register(self, tool: Tool) -> None:
        """Register a tool"""
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered")
        
        self._tools[tool.name] = tool
        print(f"✅ Registered tool: {tool.name} (category: {tool.category})", flush=True)
    
    def register_function(self, func: Callable) -> None:
        """
        Register a function decorated with @tool
        
        Args:
            func: Decorated function with _tool attribute
        """
        if not hasattr(func, '_tool'):
            raise ValueError(
                f"Function {func.__name__} is not decorated with @tool. "
                "Use @tool decorator before registering."
            )
        
        self.register(func._tool)
    
    def get_tool(self, name: str) -> Optional[Tool]:
        """Get a tool by name"""
        return self._tools.get(name)
    
    def list_tools(
        self, 
        category: Optional[str] = None,
        requires_auth: Optional[bool] = None
    ) -> List[Tool]:
        """
        List all tools, optionally filtered by category or auth requirement
        
        Args:
            category: Filter by category
            requires_auth: Filter by auth requirement
        """
        tools = list(self._tools.values())
        
        if category is not None:
            tools = [t for t in tools if t.category == category]
        
        if requires_auth is not None:
            tools = [t for t in tools if t.requires_auth == requires_auth]
        
        return tools
    
    def get_tools_by_names(self, tool_names: List[str]) -> List[Tool]:
        """
        Get specific tools by their names
        
        Args:
            tool_names: List of tool names to retrieve
            
        Returns:
            List of Tool objects (skips unknown tools)
        """
        tools = []
        for name in tool_names:
            tool = self.get_tool(name)
            if tool:
                tools.append(tool)
            else:
                print(f"⚠️ Warning: Tool '{name}' not found in registry", flush=True)
        return tools
    
    def get_openai_tools(
        self,
        tool_names: Optional[List[str]] = None,
        category: Optional[str] = None,
        requires_auth: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """
        Get OpenAI tool schemas for specified tools or filtered tools
        
        Args:
            tool_names: Specific tool names to include (if provided, ignores other filters)
            category: Filter by category (only if tool_names not provided)
            requires_auth: Filter by auth requirement (only if tool_names not provided)
        
        Returns:
            List of OpenAI-compatible tool schemas
        """
        if tool_names is not None:
            # Get specific tools by name
            tools = self.get_tools_by_names(tool_names)
        else:
            # Get filtered tools
            tools = self.list_tools(category=category, requires_auth=requires_auth)
        
        return [t.to_openai_schema() for t in tools]
    
    def get_all_schemas(self) -> List[Dict[str, Any]]:
        """Get all OpenAI tool schemas"""
        return [t.to_openai_schema() for t in self._tools.values()]
    
    async def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        context: ToolContext
    ) -> Dict[str, Any]:
        """
        Execute a tool with given arguments and context
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Arguments from LLM (keyword args for the function)
            context: Context with session_id, etc. (not visible to LLM)
        
        Returns:
            Tool execution result
        """
        tool = self.get_tool(tool_name)
        if not tool:
            return {
                "success": False,
                "message": f"Unknown tool: {tool_name}"
            }
        
        try:
            # Merge context into arguments
            kwargs = {"context": context, **arguments}
            
            # Execute tool
            if tool.is_async:
                result = await tool.handler(**kwargs)
            else:
                result = tool.handler(**kwargs)
            
            return result
        
        except Exception as e:
            print(f"❌ Error executing tool {tool_name}: {str(e)}", flush=True)
            import traceback
            traceback.print_exc()
            
            return {
                "success": False,
                "message": f"Error executing {tool_name}: {str(e)}"
            }
    
    def get_tool_descriptions_for_prompt(
        self,
        category: Optional[str] = None,
        requires_auth: Optional[bool] = None
    ) -> str:
        """
        Generate a human-readable description of available tools for system prompt
        
        Args:
            category: Filter by category
            requires_auth: Filter by auth requirement
        
        Returns:
            Formatted string describing available tools
        """
        tools = self.list_tools(category=category, requires_auth=requires_auth)
        
        if not tools:
            return "No tools available."
        
        # Group by category
        by_category: Dict[str, List[Tool]] = {}
        for tool in tools:
            cat = tool.category or "General"
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(tool)
        
        # Build description
        lines = ["Available Tools:"]
        for cat, cat_tools in sorted(by_category.items()):
            lines.append(f"\n{cat.upper()} TOOLS:")
            for tool in cat_tools:
                lines.append(f"  - {tool.name}: {tool.description}")
        
        return "\n".join(lines)


# Global registry instance
tool_registry = ToolRegistry()

