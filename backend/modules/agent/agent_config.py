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
    
    # Custom Strategies (V2 - LLM-Native)
    'create_trading_strategy',    # Create rule-based strategies
    'test_strategy',               # Test strategy on a ticker
    'scan_with_strategy',          # Scan multiple tickers for opportunities
    'list_strategies',             # List all strategies
    'get_strategy_details',        # Get strategy details
    'delete_strategy',             # Delete a strategy
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

