"""
Agent Configuration - single flat agent

Single agent with full tool access and context management (session pruning + compaction).
"""
from config import Config
from .prompts import get_agent_system_prompt


async def create_agent(context, user_id: str = None, skill_ids: list[str] = None, bot_context: dict = None):
    """
    Create the agent with full tool access.

    If bot_context is provided, builds a bot-specific system prompt instead
    of the generic Finch agent prompt. bot_context should contain keys like:
      bot_name, bot_id, mandate, memory_md, positions_json,
      recent_ticks_summary, platform, connections
    """
    from .base_agent import BaseAgent

    if bot_context:
        from modules.bots.prompts import build_chat_system_prompt
        from .prompts import build_skills_prompt, MEMORY_PROMPT

        skills_section = build_skills_prompt(skill_ids or [])
        system_prompt = build_chat_system_prompt(
            bot_name=bot_context.get("bot_name", "Trading Bot"),
            bot_id=bot_context.get("bot_id", ""),
            mandate=bot_context.get("mandate", ""),
            memory_md=bot_context.get("memory_md", ""),
            positions_json=bot_context.get("positions_json", "None"),
            recent_ticks_summary=bot_context.get("recent_ticks_summary", ""),
            platform=bot_context.get("platform", "kalshi"),
            connections=bot_context.get("connections"),
            skills_prompt=skills_section,
            capital_balance=bot_context.get("capital_balance"),
            per_position_usd=bot_context.get("per_position_usd"),
            max_positions=bot_context.get("max_positions"),
            wakeup_reason=bot_context.get("wakeup_reason"),
            wakeup_type=bot_context.get("wakeup_type"),
            wakeup_context=bot_context.get("wakeup_context"),
        )
        # Append memory guidance
        system_prompt += MEMORY_PROMPT
    else:
        system_prompt = await get_agent_system_prompt(user_id, skill_ids)

    return BaseAgent(
        context=context,
        system_prompt=system_prompt,
        model=Config.AGENT_LLM_MODEL,
        tool_names=Config.AGENT_TOOLS,
        enable_tool_streaming=True
    )
