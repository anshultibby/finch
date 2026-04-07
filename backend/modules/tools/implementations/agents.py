"""
Agent creation tool implementation.

Sub-agents share the same sandbox filesystem as the main agent.
create_agent writes an entry to /home/user/agents.md so the agent
can list/reference agents via bash without a dedicated tool.
"""
import logging
from typing import Optional, Dict, Any

from modules.agent.context import AgentContext
from modules.tools.responses import ToolSuccess

logger = logging.getLogger(__name__)

WORKSPACE_DIR = "/home/user"
AGENTS_MANIFEST = f"{WORKSPACE_DIR}/agents.md"


async def create_agent_impl(
    context: AgentContext,
    name: str,
    task: str,
    platform: str = "research",
    capital_usd: Optional[float] = None,
    icon: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a new sub-agent and queue its initial task.

    The task is saved as the first message in the agent's chat.
    Users can open the agent chat to run it and peek at progress.

    agents.md is a plain markdown file the agent can read with bash:
        bash("cat /home/user/agents.md")
    """
    from core.database import get_db_session
    from crud.bots import create_bot
    from crud.chat_async import create_chat
    from models.chat_models import ChatMessageDB
    from schemas.bots import CreateBotRequest
    import uuid

    async with get_db_session() as db:
        req = CreateBotRequest(
            name=name.strip(),
            platform=platform,
            capital_amount=capital_usd,
            icon=icon or "🤖",
        )
        bot = await create_bot(db, context.user_id, req)
        bot_id = str(bot.id)

        # Create first chat for this agent
        chat_id = str(uuid.uuid4())
        from models.chat_models import Chat
        chat = Chat(
            chat_id=chat_id,
            user_id=context.user_id,
            bot_id=bot_id,
            title=name.strip(),
        )
        db.add(chat)

        # Save task as first user message so the agent can be triggered later
        from datetime import datetime, timezone
        msg = ChatMessageDB(
            chat_id=chat_id,
            role="user",
            content=task,
            timestamp=datetime.now(timezone.utc),
        )
        db.add(msg)
        await db.commit()

    # Write manifest entry to sandbox (fire-and-forget)
    import asyncio
    asyncio.create_task(_register_agent_in_manifest(context, bot, platform, capital_usd))

    return ToolSuccess(
        data={"agent_id": bot_id, "chat_id": chat_id, "name": bot.name},
        message=f"Agent '{bot.name}' created with task queued (chat_id={chat_id}).",
    )


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
