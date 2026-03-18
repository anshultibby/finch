"""
Wakeup Executor — runs a bot wakeup as a full agent chat.

When a scheduled wakeup fires:
  1. Creates a bot-scoped chat thread
  2. Builds bot context (strategy, positions, operational memory, etc.)
  3. Injects wakeup reason into the system prompt
  4. Runs the full LLM agent loop (same as user chat)
  5. All messages are saved to the chat (visible in UI)
"""
import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from models.bot import BotWakeup
from models.chat_models import Chat

logger = logging.getLogger(__name__)

WAKEUP_TIMEOUT_SECONDS = 180


async def execute_wakeup(db: AsyncSession, wakeup: BotWakeup) -> str:
    """
    Execute a bot wakeup — creates a chat and runs the full agent loop.

    Returns the chat_id of the created chat thread.
    """
    from crud import chat_async
    from crud.bots import get_bot, mark_wakeup_triggered, create_wakeup, compute_next_trigger
    from modules.chat_service import ChatService
    from modules.agent.agent_config import create_agent
    from modules.agent.context import AgentContext, generate_agent_id, register_context, unregister_context
    from schemas.chat_history import ChatHistory
    from core.config import Config

    bot = await get_bot(db, wakeup.bot_id, wakeup.user_id)
    if not bot:
        logger.error(f"Wakeup {wakeup.id}: bot {wakeup.bot_id} not found, marking as triggered")
        await mark_wakeup_triggered(db, wakeup, chat_id=None)
        return ""

    # 1. Create a bot-scoped chat
    chat_id = str(uuid.uuid4())
    chat = Chat(
        chat_id=chat_id,
        user_id=wakeup.user_id,
        bot_id=wakeup.bot_id,
        title=f"Wakeup: {wakeup.reason[:60]}",
        icon="⏰",
    )
    db.add(chat)
    await db.commit()
    await db.refresh(chat)

    # 2. Mark wakeup as triggered
    await mark_wakeup_triggered(db, wakeup, chat_id)

    # 3. Build bot context (same as chat_service._build_bot_context)
    service = ChatService()
    bot_context = await service._build_bot_context(db, wakeup.bot_id, wakeup.user_id)
    if not bot_context:
        logger.error(f"Wakeup {wakeup.id}: failed to build bot context")
        return chat_id

    # Inject wakeup context into bot_context so the system prompt includes it
    bot_context["wakeup_reason"] = wakeup.reason
    bot_context["wakeup_type"] = wakeup.trigger_type
    bot_context["wakeup_context"] = wakeup.context

    # 4. Create agent with wakeup-aware context
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

    # 5. Build initial message context and history
    history = ChatHistory.from_db_messages([], chat_id, wakeup.user_id)

    # Use the wakeup's custom message if set, otherwise default
    trigger_message = wakeup.message or "Wakeup triggered. Proceed."

    current_sequence = 0
    await chat_async.create_message(db, chat_id, "user", trigger_message, current_sequence)
    current_sequence += 1
    history.add_user_message(trigger_message)

    # 6. Run the full agent loop
    logger.info(f"Wakeup {wakeup.id}: running agent loop for bot '{bot.name}' — {wakeup.reason[:80]}")
    pending_assistant_msg = None

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
                    pending_assistant_msg = {"content": content, "tool_calls": tool_calls}
                else:
                    seq = current_sequence
                    current_sequence += 1
                    await chat_async.create_message(db, chat_id, "assistant", content, seq)

            elif event.event == "tools_end":
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
                    seq = current_sequence
                    current_sequence += 1 + len(tool_messages)
                    await chat_async.create_message(
                        db, chat_id, "assistant",
                        pending_assistant_msg["content"], seq,
                        tool_calls=pending_assistant_msg["tool_calls"],
                        tool_results=tool_results if tool_results else None,
                    )
                    seq += 1
                    for tool_msg in tool_messages:
                        msg_content = tool_msg.get("content", "")
                        if isinstance(msg_content, list):
                            msg_content = json.dumps(msg_content)
                        await chat_async.create_message(
                            db, chat_id, "tool", msg_content, seq,
                            tool_call_id=tool_msg.get("tool_call_id"),
                            name=tool_msg.get("name"),
                        )
                        seq += 1

                pending_assistant_msg = None

    except asyncio.TimeoutError:
        logger.error(f"Wakeup {wakeup.id}: agent loop timed out")
        await chat_async.create_message(
            db, chat_id, "assistant",
            "Wakeup execution timed out.", current_sequence,
        )
    except Exception as e:
        logger.exception(f"Wakeup {wakeup.id}: agent loop failed: {e}")
        await chat_async.create_message(
            db, chat_id, "assistant",
            f"Wakeup execution failed: {str(e)[:200]}", current_sequence,
        )
    finally:
        unregister_context(chat_id, agent_context)
        await chat_async.set_chat_processing(db, chat_id, is_processing=False)

    # Auto-schedule next occurrence for recurring wakeups
    if wakeup.recurrence and bot.enabled:
        now = datetime.now(timezone.utc)
        next_trigger = compute_next_trigger(wakeup.recurrence, now)
        if next_trigger:
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
                logger.error(f"Wakeup {wakeup.id}: failed to schedule next recurrence: {e}")

    logger.info(f"Wakeup {wakeup.id}: complete, chat_id={chat_id}")
    return chat_id
