"""
Agent Configuration — one prompt for all agents (main + sub-agents).
"""
from core.config import Config
from .prompts import get_agent_system_prompt


async def create_agent(context, user_id: str = None, skill_ids: list[str] = None, investor_persona: str = None):
    """Create an agent with the base system prompt."""
    from .base_agent import BaseAgent

    system_prompt = await get_agent_system_prompt(user_id, skill_ids, investor_persona=investor_persona)

    return BaseAgent(
        context=context,
        system_prompt=system_prompt,
        model=Config.AGENT_LLM_MODEL,
        tool_names=Config.AGENT_TOOLS,
        enable_tool_streaming=True,
    )
