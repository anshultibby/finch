"""
Agent Configuration — one prompt for all agents (main + sub-agents).
"""
import json
from core.config import Config
from .prompts import get_agent_system_prompt


async def create_agent(context, user_id: str = None, skill_ids: list[str] = None, investor_persona: str = None):
    """Create an agent with the base system prompt."""
    from .base_agent import BaseAgent

    system_prompt = await get_agent_system_prompt(user_id, skill_ids, investor_persona=investor_persona)

    page_context = context.data.get("page_context") if context.data else None
    page_context_text = None
    if page_context:
        page_context_text = f"<page_context>\nThe user is currently viewing this page. Use this data as context — don't re-fetch what's already here unless the user asks for something beyond it.\n{json.dumps(page_context, indent=2)}\n</page_context>"

    return BaseAgent(
        context=context,
        system_prompt=system_prompt,
        system_prompt_suffix=page_context_text,
        model=Config.AGENT_LLM_MODEL,
        tool_names=Config.AGENT_TOOLS,
        enable_tool_streaming=True,
    )
