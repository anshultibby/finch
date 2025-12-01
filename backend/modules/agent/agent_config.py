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
    # Portfolio & Brokerage
    'get_portfolio',
    'request_brokerage_connection',
    
    # Market Intelligence
    'get_reddit_trending_stocks',
    'get_reddit_ticker_sentiment',
    'compare_reddit_sentiment',
    'get_fmp_data',
    
    # Visualization
    'create_chart',
    
    # Trading Analytics
    'get_transaction_history',
    'analyze_portfolio_performance',
    'identify_trading_patterns',
    
    
    # Financial Code Generation (NEW - Manus-inspired)
    'generate_financial_code',     # Generate Python code from description
    'execute_financial_code',      # Execute code on ticker
    'batch_execute_code',          # Execute code on multiple tickers
    
    # File Management
    'list_chat_files',             # List files in current chat
    'write_chat_file',             # Write file to chat directory
    'read_chat_file',              # Read file from chat directory
    'replace_in_chat_file',        # Edit files (Manus-style)
    'find_in_chat_file',           # Search files with regex
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

