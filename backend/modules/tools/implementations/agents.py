"""
Agent creation tool implementation — creates a sub-agent chat with a queued task.
"""
import logging
import uuid
from typing import Optional, Dict, Any

from modules.agent.context import AgentContext
from modules.tools.responses import ToolSuccess

logger = logging.getLogger(__name__)


async def create_agent_impl(
    context: AgentContext,
    name: str,
    task: str,
    platform: str = "research",
    capital_usd: Optional[float] = None,
    icon: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a new sub-agent chat with a queued initial task.
    The task is saved as the first message so the agent can be run later.
    """
    from core.database import get_db_session
    from models.chat_models import Chat, ChatMessageDB
    from datetime import datetime, timezone

    chat_id = str(uuid.uuid4())
    agent_id = str(uuid.uuid4())

    async with get_db_session() as db:
        chat = Chat(
            chat_id=chat_id,
            user_id=context.user_id,
            title=name.strip(),
            icon=icon or "🤖",
        )
        db.add(chat)

        msg = ChatMessageDB(
            chat_id=chat_id,
            role="user",
            content=task,
            sequence=0,
            timestamp=datetime.now(timezone.utc),
        )
        db.add(msg)
        await db.commit()

    return ToolSuccess(
        data={"agent_id": agent_id, "chat_id": chat_id, "name": name.strip()},
        message=f"Agent '{name.strip()}' created with task queued (chat_id={chat_id}).",
    )
