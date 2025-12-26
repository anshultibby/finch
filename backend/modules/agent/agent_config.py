"""
Agent Configuration - Centralized agent creation and tool registry

Factory functions for creating properly configured agents.
Currently supports one main chat agent, but designed for easy expansion.
"""
from typing import List


# ============================================================================
# MAIN CHAT AGENT TOOLS
# ============================================================================

# All tools available to the main Finch chat agent
MAIN_AGENT_TOOLS = [
    # Code Execution (Primary Tool)
    'execute_code',                # Execute Python code - main interface for all operations
    
    # File Management
    'write_chat_file',             # Write file to chat directory
    'read_chat_file',              # Read file from chat directory
    'replace_in_chat_file',        # Edit files (search/replace)
    
    # Custom ETF Builder
    'build_custom_etf',            # Build custom ETF portfolios with weighting strategies
]


# ============================================================================
# AGENT FACTORY FUNCTIONS
# ============================================================================

def create_main_agent(context, system_prompt: str, model: str):
    """
    Create a properly configured main chat agent.
    
    Args:
        context: AgentContext with user_id, chat_id, data
        system_prompt: System prompt for the agent
        model: LLM model name
        
    Returns:
        BaseAgent instance configured with all main agent tools
    """
    from .base_agent import BaseAgent
    
    return BaseAgent(
        context=context,
        system_prompt=system_prompt,
        model=model,
        tool_names=MAIN_AGENT_TOOLS,
        enable_tool_streaming=True
    )


# ============================================================================
# CONVENIENCE FUNCTIONS (for backward compatibility)
# ============================================================================

def get_main_agent_tools() -> List[str]:
    """Get the list of tools available to the main chat agent"""
    return MAIN_AGENT_TOOLS.copy()

