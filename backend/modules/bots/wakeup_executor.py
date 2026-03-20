"""
Wakeup Executor — runs a bot wakeup as a full agent chat.

When a scheduled wakeup fires:
  1. Checks bot is enabled (skips disabled/paused bots)
  2. Builds bot context (strategy, positions, operational memory, etc.)
  3. Injects wakeup reason into the system prompt
  4. Runs the full LLM agent loop, buffering messages in memory
  5. If the agent did meaningful work (tool calls), persists a bot-scoped chat
  6. If nothing meaningful happened, no chat is created (avoids clutter)
  7. On failure, retries up to MAX_RETRIES before marking as failed
"""
import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from models.bot import BotWakeup
from models.chat_models import Chat

logger = logging.getLogger(__name__)

WAKEUP_TIMEOUT_SECONDS = 180
MAX_RETRIES = 2


async def _persist_wakeup_chat(
    db: AsyncSession,
    chat_id: str,
    wakeup: BotWakeup,
    buffered_messages: list,
    title: str,
    icon: str,
    extra_message: Optional[str] = None,
) -> None:
    """Create a bot-scoped chat and persist all buffered messages."""
    from crud import chat_async

    chat = Chat(
        chat_id=chat_id,
        user_id=wakeup.user_id,
        bot_id=wakeup.bot_id,
        title=title,
        icon=icon,
    )
    db.add(chat)
    await db.commit()
    await db.refresh(chat)

    seq = 0
    for role, content, kwargs in buffered_messages:
        await chat_async.create_message(db, chat_id, role, content, seq, **kwargs)
        seq += 1

    if extra_message:
        await chat_async.create_message(db, chat_id, "assistant", extra_message, seq)

    await chat_async.set_chat_processing(db, chat_id, is_processing=False)


async def execute_wakeup(db: AsyncSession, wakeup: BotWakeup) -> str:
    """
    Execute a bot wakeup — runs the agent loop and only creates a chat
    if the agent did meaningful work (tool calls).

    Returns the chat_id if a chat was created, or empty string.
    """
    from crud.bots import get_bot, mark_wakeup_triggered, mark_wakeup_retrying, mark_wakeup_failed, create_wakeup, compute_next_trigger
    from modules.chat_service import ChatService
    from modules.agent.agent_config import create_agent
    from modules.agent.context import AgentContext, generate_agent_id, register_context, unregister_context
    from schemas.chat_history import ChatHistory
    from core.config import Config

    bot = await get_bot(db, wakeup.bot_id, wakeup.user_id)
    if not bot:
        logger.error(f"Wakeup {wakeup.id}: bot {wakeup.bot_id} not found, marking as triggered")
        await mark_wakeup_triggered(db, wakeup)
        return ""

    # Guard: skip wakeups for disabled bots
    if not bot.enabled:
        logger.info(f"Wakeup {wakeup.id}: bot '{bot.name}' is disabled, skipping")
        await mark_wakeup_triggered(db, wakeup)
        # Don't reschedule recurring wakeups for disabled bots
        return ""

    # 1. Build bot context
    service = ChatService()
    bot_context = await service._build_bot_context(db, wakeup.bot_id, wakeup.user_id)
    if not bot_context:
        logger.error(f"Wakeup {wakeup.id}: failed to build bot context")
        await mark_wakeup_failed(db, wakeup, error="Failed to build bot context")
        return ""

    # Inject wakeup context into bot_context so the system prompt includes it
    bot_context["wakeup_reason"] = wakeup.reason
    bot_context["wakeup_type"] = wakeup.trigger_type
    bot_context["wakeup_context"] = wakeup.context

    # 2. Create agent (use a provisional chat_id for the agent context)
    chat_id = str(uuid.uuid4())
    cancel_event = asyncio.Event()
    agent_context = AgentContext(
        agent_id=generate_agent_id(),
        user_id=wakeup.user_id,
        chat_id=chat_id,
        skill_ids=[],
        data={"bot_id": str(wakeup.bot_id)},
        cancel_event=cancel_event,
    )
    register_context(chat_id, agent_context)

    agent = await create_agent(
        agent_context,
        user_id=wakeup.user_id,
        skill_ids=[],
        bot_context=bot_context,
    )

    # 3. Build initial message context and history
    history = ChatHistory.from_db_messages([], chat_id, wakeup.user_id)
    trigger_message = wakeup.message or "Wakeup triggered. Proceed."
    history.add_user_message(trigger_message)

    # 4. Run the agent loop, buffering all messages in memory
    logger.info(f"Wakeup {wakeup.id}: running agent loop for bot '{bot.name}' — {wakeup.reason[:80]}")
    buffered_messages = [("user", trigger_message, {})]
    had_tool_calls = False
    pending_assistant_msg = None
    failed = False
    error_message = None

    try:
        async for event in agent.process_message_stream(
            message=trigger_message,
            chat_history=history,
            history_limit=Config.CHAT_HISTORY_LIMIT,
        ):
            if event.event == "message_end":
                tool_calls = event.data.get("tool_calls")
                content = event.data.get("content", "")

                if tool_calls:
                    had_tool_calls = True
                    pending_assistant_msg = {"content": content, "tool_calls": tool_calls}
                else:
                    buffered_messages.append(("assistant", content, {}))

            elif event.event == "tools_end":
                had_tool_calls = True
                tool_messages = event.data.get("tool_messages", [])
                execution_results = event.data.get("execution_results", [])

                tool_results = {}
                for exec_result in execution_results:
                    tcid = exec_result.get("tool_call_id")
                    if tcid:
                        result_data = exec_result.get("result_data", {})
                        tool_results[tcid] = {
                            "status": exec_result.get("status", "completed"),
                            "error": exec_result.get("error"),
                            "result_summary": result_data.get("message") if isinstance(result_data, dict) else None,
                        }
                        if isinstance(result_data, dict):
                            stdout = result_data.get("stdout")
                            stderr = result_data.get("stderr")
                            if stdout is not None or stderr is not None:
                                tool_results[tcid]["code_output"] = {"stdout": stdout or "", "stderr": stderr or ""}

                if pending_assistant_msg:
                    buffered_messages.append(("assistant", pending_assistant_msg["content"], {
                        "tool_calls": pending_assistant_msg["tool_calls"],
                        "tool_results": tool_results if tool_results else None,
                    }))
                    for tool_msg in tool_messages:
                        msg_content = tool_msg.get("content", "")
                        if isinstance(msg_content, list):
                            msg_content = json.dumps(msg_content)
                        buffered_messages.append(("tool", msg_content, {
                            "tool_call_id": tool_msg.get("tool_call_id"),
                            "name": tool_msg.get("name"),
                        }))

                pending_assistant_msg = None

    except asyncio.TimeoutError:
        error_message = "Agent loop timed out"
        logger.error(f"Wakeup {wakeup.id}: {error_message}")
        failed = True
    except Exception as e:
        error_message = str(e)
        logger.exception(f"Wakeup {wakeup.id}: agent loop failed: {e}")
        failed = True
    finally:
        unregister_context(chat_id, agent_context)

    # 5. Handle failure with retry
    if failed:
        current_retries = wakeup.retry_count or 0
        if current_retries < MAX_RETRIES:
            await mark_wakeup_retrying(db, wakeup, error=error_message)
            logger.warning(
                f"Wakeup {wakeup.id}: retry {wakeup.retry_count}/{MAX_RETRIES} — {error_message}"
            )
            return ""
        else:
            logger.error(
                f"Wakeup {wakeup.id}: max retries exhausted ({MAX_RETRIES}), marking as failed"
            )
            await mark_wakeup_failed(db, wakeup, error=error_message)
            await _persist_wakeup_chat(
                db, chat_id, wakeup, buffered_messages,
                title=f"Wakeup FAILED: {wakeup.reason[:60]}",
                icon="❌",
                extra_message=f"Wakeup execution failed after {MAX_RETRIES} retries. Error: {error_message or 'unknown'}",
            )
            await _reschedule_if_recurring(db, wakeup, bot)
            return chat_id

    # 6. Decide whether to persist a chat (success path)
    if not had_tool_calls:
        logger.info(f"Wakeup {wakeup.id}: no tool calls, skipping chat creation")
        await mark_wakeup_triggered(db, wakeup)
    else:
        await _persist_wakeup_chat(
            db, chat_id, wakeup, buffered_messages,
            title=f"Wakeup: {wakeup.reason[:60]}",
            icon="⏰",
        )
        await mark_wakeup_triggered(db, wakeup, chat_id=chat_id)
        logger.info(f"Wakeup {wakeup.id}: complete, chat_id={chat_id}")

    await _reschedule_if_recurring(db, wakeup, bot)
    return chat_id if had_tool_calls else ""


async def _reschedule_if_recurring(db: AsyncSession, wakeup: BotWakeup, bot) -> None:
    """Auto-schedule the next occurrence of a recurring wakeup.

    Logs errors loudly rather than silently dropping the recurrence chain.
    """
    from crud.bots import create_wakeup, compute_next_trigger

    if not wakeup.recurrence:
        return

    if not bot.enabled:
        logger.warning(
            f"Wakeup {wakeup.id}: skipping recurrence reschedule — bot '{bot.name}' is disabled"
        )
        return

    now = datetime.now(timezone.utc)
    next_trigger = compute_next_trigger(wakeup.recurrence, now)

    if not next_trigger:
        logger.error(
            f"Wakeup {wakeup.id}: RECURRENCE BROKEN — compute_next_trigger returned None "
            f"for pattern '{wakeup.recurrence}'. Bot '{bot.name}' will NOT receive future wakeups "
            f"until this is fixed."
        )
        return

    try:
        next_wakeup = await create_wakeup(
            db=db,
            bot_id=wakeup.bot_id,
            user_id=wakeup.user_id,
            trigger_at=next_trigger,
            reason=wakeup.reason,
            trigger_type=wakeup.trigger_type,
            context=wakeup.context,
            recurrence=wakeup.recurrence,
            message=wakeup.message,
        )
        logger.info(
            f"Wakeup {wakeup.id}: scheduled next recurrence {next_wakeup.id} at {next_trigger}"
        )
    except Exception as e:
        logger.error(
            f"Wakeup {wakeup.id}: RECURRENCE FAILED — could not schedule next occurrence: {e}. "
            f"Bot '{bot.name}' (pattern: {wakeup.recurrence}) will NOT receive future wakeups."
        )
