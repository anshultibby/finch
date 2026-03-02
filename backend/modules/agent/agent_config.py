"""
Agent Configuration - single flat agent

Single agent with full tool access and context management (session pruning + compaction).
"""
from config import Config
from .prompts import get_agent_system_prompt


async def create_agent(context, user_id: str = None, skill_ids: list[str] = None):
    """
    Create the agent with full tool access.

    The agent handles everything directly — research, code execution, file
    management, domain tools. Context is managed via session pruning (transient,
    per LLM call) and compaction (persistent, stored in DB).
    """
    from .base_agent import BaseAgent

    system_prompt = await get_agent_system_prompt(user_id, skill_ids)

    return BaseAgent(
        context=context,
        system_prompt=system_prompt,
        model=Config.AGENT_LLM_MODEL,
        tool_names=Config.AGENT_TOOLS,
        enable_tool_streaming=True
    )
