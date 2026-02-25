"""
Agent Configuration - Two-tier agent system

Based on Anthropic's "Effective harnesses for long-running agents":
- Planner Agent: Lightweight coordinator - plans, delegates, reviews
- Executor Agent: Does all the work - research, code, save results

All agent configuration (model, tools, prompts) is centralized here.
"""
from config import Config
from .prompts import get_planner_agent_prompt, get_executor_agent_prompt


async def create_planner_agent(context, user_id: str = None, skill_ids: list[str] = None):
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

    system_prompt = await get_planner_agent_prompt(user_id, skill_ids)

    return BaseAgent(
        context=context,
        system_prompt=system_prompt,
        model=Config.PLANNER_LLM_MODEL,
        tool_names=Config.PLANNER_AGENT_TOOLS,
        enable_tool_streaming=True
    )


async def create_executor_agent(context, user_id: str = None, skill_ids: list[str] = None, chat_logger=None):
    """
    Create the Executor Agent.

    Executor Agent (does all the work):
    - Receives ONE task from Planner
    - Researches (web search, scrape)
    - Writes and executes code
    - Saves all results to files
    - Calls finish_execution when done
    
    Args:
        context: AgentContext for this executor instance
        user_id: User ID
        skill_ids: List of skill IDs to include
        chat_logger: Optional ChatLogger for separate conversation tracking
    """
    from .base_agent import BaseAgent

    system_prompt = await get_executor_agent_prompt(user_id, skill_ids)

    return BaseAgent(
        context=context,
        system_prompt=system_prompt,
        model=Config.EXECUTOR_LLM_MODEL,
        tool_names=Config.EXECUTOR_AGENT_TOOLS,
        enable_tool_streaming=True,
        chat_logger=chat_logger
    )
