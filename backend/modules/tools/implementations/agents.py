"""
Agent creation tool implementation.

Sub-agents share the same sandbox filesystem as the main agent.
create_agent writes an entry to /home/user/agents.md so the agent
can list/reference agents via bash without a dedicated tool.
"""
import logging
from typing import Optional, Dict, Any

from modules.agent.context import AgentContext

logger = logging.getLogger(__name__)

WORKSPACE_DIR = "/home/user"
AGENTS_MANIFEST = f"{WORKSPACE_DIR}/agents.md"


async def create_agent_impl(
    context: AgentContext,
    name: str,
    platform: str = "research",
    capital_usd: Optional[float] = None,
    icon: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a new sub-agent and register it in /home/user/agents.md.

    agents.md is a plain markdown file the agent can read with bash:
        bash("cat /home/user/agents.md")
    """
    from core.database import get_db_session
    from crud.bots import create_bot
    from schemas.bots import CreateBotRequest
    from datetime import datetime

    async with get_db_session() as db:
        req = CreateBotRequest(
            name=name.strip(),
            platform=platform,
            capital_amount=capital_usd,
            icon=icon or "🤖",
        )
        bot = await create_bot(db, context.user_id, req)

    # Write manifest entry to sandbox (fire-and-forget)
    import asyncio
    asyncio.create_task(_register_agent_in_manifest(context, bot, platform, capital_usd))

    return {
        "success": True,
        "agent_id": str(bot.id),
        "name": bot.name,
        "platform": platform,
        "message": (
            f"Agent '{bot.name}' created (id={bot.id}). "
            f"Registered in {AGENTS_MANIFEST}."
        ),
    }


async def _register_agent_in_manifest(context, bot, platform: str, capital_usd) -> None:
    """Append a line to agents.md in the sandbox."""
    from datetime import datetime, timezone

    try:
        from modules.tools.implementations.code_execution import (
            get_or_create_sandbox,
            _build_sandbox_env,
        )

        created = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        capital_str = f" — ${capital_usd:.0f}" if capital_usd else ""
        entry = f"- {bot.icon or '🤖'} **{bot.name}** (id: `{bot.id}`) — {platform}{capital_str} — created {created}"

        cmd = "\n".join([
            f"[ ! -f {AGENTS_MANIFEST} ] && echo '# Agents\\n' > {AGENTS_MANIFEST}",
            f"echo '{entry}' >> {AGENTS_MANIFEST}",
        ])

        envs = await _build_sandbox_env(context)
        entry_obj = await get_or_create_sandbox(context.user_id, envs)
        await entry_obj.sbx.commands.run(cmd, cwd=WORKSPACE_DIR, timeout=15)

    except Exception as e:
        logger.warning(f"Could not update agents.md: {e}")
