"""
Agent Configuration - Two-tier agent system

Based on Anthropic's "Effective harnesses for long-running agents":
- Planner Agent: Lightweight coordinator - plans, delegates, reviews
- Executor Agent: Does all the work - research, code, save results

All agent configuration (model, tools, prompts) is centralized here.
"""
from config import Config
from .prompts import get_planner_agent_prompt, get_executor_agent_prompt


def create_planner_agent(context):
    """
    Create the Planner Agent.
    
    Planner Agent (lightweight coordinator):
    - Understands user request
    - Creates tasks.md with checklist
    - Delegates ONE task at a time to Executor
    - Reviews results and updates tasks
    - Does NOT execute code or research itself
    """
    from .base_agent import BaseAgent
    
    return BaseAgent(
        context=context,
        system_prompt=get_planner_agent_prompt(),
        model=Config.PLANNER_LLM_MODEL,
        tool_names=Config.PLANNER_AGENT_TOOLS,
        enable_tool_streaming=True
    )


def create_executor_agent(context):
    """
    Create the Executor Agent.
    
    Executor Agent (does all the work):
    - Receives ONE task from Planner
    - Researches (web search, scrape)
    - Writes and executes code
    - Saves all results to files
    - Calls finish_execution when done
    """
    from .base_agent import BaseAgent
    
    return BaseAgent(
        context=context,
        system_prompt=get_executor_agent_prompt(),
        model=Config.EXECUTOR_LLM_MODEL,
        tool_names=Config.EXECUTOR_AGENT_TOOLS,
        enable_tool_streaming=True
    )
