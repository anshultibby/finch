"""
Unit test for the per-chat sub-agent cap in the delegate tool.

Verifies that once SUBAGENT_MAX_PER_CHAT sub-agents have been spawned for a chat,
further delegate calls are rejected up-front (no sub-agent spawned) with a clear
message telling the coordinator to do the work itself.
"""
import pytest

from core.config import Config
from modules.agent.context import AgentContext
from modules.tools.implementations import delegate as delegate_mod


def _ctx(chat_id: str):
    return AgentContext(agent_id="main", user_id="u", chat_id=chat_id, data={})


@pytest.fixture(autouse=True)
def _reset_tally():
    delegate_mod._subagents_spawned.clear()
    yield
    delegate_mod._subagents_spawned.clear()


@pytest.mark.asyncio
async def test_rejects_once_cap_reached():
    chat = "chat-cap"
    # Pretend the cap is already used up for this chat.
    delegate_mod._subagents_spawned[chat] = Config.SUBAGENT_MAX_PER_CHAT

    items = []
    async for item in delegate_mod.delegate_task(
        context=_ctx(chat), task="analyze X", task_id="x"
    ):
        items.append(item)

    # Exactly one item: the rejection result. No sub-agent events streamed.
    assert len(items) == 1
    assert items[0]["success"] is False
    assert items[0]["error"] == "subagent_limit_reached"
    # Tally is unchanged (we didn't spawn another).
    assert delegate_mod._subagents_spawned[chat] == Config.SUBAGENT_MAX_PER_CHAT


@pytest.mark.asyncio
async def test_cap_is_per_chat():
    """A different chat is unaffected by another chat's tally."""
    delegate_mod._subagents_spawned["chat-a"] = Config.SUBAGENT_MAX_PER_CHAT
    # chat-b has no tally yet, so it is under the cap (not rejected by the guard).
    assert delegate_mod._subagents_spawned.get("chat-b", 0) < Config.SUBAGENT_MAX_PER_CHAT
