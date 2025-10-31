"""
Tool execution logic for the AI agent - uses tool registry
"""
from typing import Dict, Any
from modules.tools import ToolContext, tool_registry


async def execute_tool(
    function_name: str,
    function_args: Dict[str, Any],
    session_id: str
) -> Dict[str, Any]:
    """
    Execute a tool using the tool registry
    
    Args:
        function_name: Name of the tool to execute
        function_args: Arguments to pass to the tool (from LLM)
        session_id: User session ID for context
        
    Returns:
        Tool execution result as dictionary
    """
    print(f"🔧 Executing tool: {function_name} for session: {session_id}", flush=True)
    
    # Create context (secure data not visible to LLM)
    context = ToolContext(
        session_id=session_id,
        user_id=None  # Can add user_id later if needed
    )
    
    # Execute tool through registry
    result = await tool_registry.execute_tool(
        tool_name=function_name,
        arguments=function_args,
        context=context
    )
    
    # Log result summary
    if result.get("success"):
        print(f"✅ {function_name} completed successfully", flush=True)
    else:
        print(f"❌ {function_name} failed: {result.get('message', 'Unknown error')}", flush=True)
    
    return result

