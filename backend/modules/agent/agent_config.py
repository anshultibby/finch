"""
Agent Configuration — one prompt for all agents (main + sub-agents).

Sub-agents use the same base prompt as the main agent.
Runtime context (positions, capital, wakeup trigger, strategy/memory) is
appended as a structured section below the base prompt.
"""
from core.config import Config
from .prompts import get_agent_system_prompt


def _build_runtime_context(bot_context: dict, skills_section: str) -> str:
    """Build the runtime context section appended to the base prompt for sub-agents."""
    lines = ["\n---\n## Agent Context\n"]

    name = bot_context.get("bot_name", "Agent")
    platform = bot_context.get("platform", "research")
    bot_id = bot_context.get("bot_id", "")
    lines.append(f"**Name:** {name}  \n**Platform:** {platform}  \n**Agent ID:** {bot_id}\n")

    # Connections
    conn = bot_context.get("connections") or {}
    if conn:
        conn_lines = [f"- **{k.title()}:** {'CONNECTED' if v else 'NOT CONNECTED'}" for k, v in conn.items()]
        lines.append("### Connections\n" + "\n".join(conn_lines) + "\n")

    # Capital
    capital_lines = []
    if bot_context.get("starting_capital") is not None:
        capital_lines.append(f"- **Starting Capital:** ${bot_context['starting_capital']:.2f}")
    if bot_context.get("capital_balance") is not None:
        capital_lines.append(f"- **Available Cash:** ${bot_context['capital_balance']:.2f}")
    if bot_context.get("per_position_usd"):
        capital_lines.append(f"- **Per-position budget:** ${bot_context['per_position_usd']:.2f}")
    if bot_context.get("max_positions"):
        capital_lines.append(f"- **Max open positions:** {bot_context['max_positions']}")
    if capital_lines:
        lines.append("### Capital\n" + "\n".join(capital_lines) + "\n")

    # Positions
    if bot_context.get("positions_json"):
        lines.append(f"### Open Positions\n{bot_context['positions_json']}\n")
    if bot_context.get("closed_positions_json"):
        lines.append(f"### Closed Positions\n{bot_context['closed_positions_json']}\n")

    # Wakeup trigger
    wakeup_reason = bot_context.get("wakeup_reason")
    if wakeup_reason:
        wakeup_lines = [
            "### Wakeup Trigger",
            f"**You were woken by a scheduled trigger.**",
            f"- **Reason:** {wakeup_reason}",
        ]
        if bot_context.get("wakeup_type"):
            wakeup_lines.append(f"- **Type:** {bot_context['wakeup_type']}")
        ctx = bot_context.get("wakeup_context") or {}
        for k, v in ctx.items():
            wakeup_lines.append(f"- **{k}:** {v}")
        wakeup_lines.append("\nAct autonomously — no user is present.")
        lines.append("\n".join(wakeup_lines) + "\n")

    # Recent activity
    if bot_context.get("recent_ticks_summary"):
        lines.append(f"### Recent Activity\n{bot_context['recent_ticks_summary']}\n")

    # Strategy and memory (filesystem content injected at session start)
    if bot_context.get("strategy_md"):
        lines.append(f"### STRATEGY.md\n{bot_context['strategy_md']}\n")
    if bot_context.get("memory_md"):
        lines.append(f"### MEMORY.md\n{bot_context['memory_md']}\n")

    if skills_section:
        lines.append(skills_section)

    return "\n".join(lines)


async def create_agent(context, user_id: str = None, skill_ids: list[str] = None, bot_context: dict = None):
    """Create an agent. Sub-agents use the same base prompt with runtime context appended."""
    from .base_agent import BaseAgent
    from .prompts import build_skills_prompt

    system_prompt = await get_agent_system_prompt(user_id, skill_ids)

    if bot_context:
        skills_section = build_skills_prompt(skill_ids or [])
        system_prompt += _build_runtime_context(bot_context, skills_section)

    return BaseAgent(
        context=context,
        system_prompt=system_prompt,
        model=Config.AGENT_LLM_MODEL,
        tool_names=Config.AGENT_TOOLS,
        enable_tool_streaming=True,
    )
