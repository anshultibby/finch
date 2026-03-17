"""
Compactor - summarizes old conversation history and persists the summary to the
database when the total history exceeds the configured token threshold.

How it works:
- After each chat turn, ChatService calls maybe_compact().
- If total estimated tokens across all DB messages exceeds COMPACTION_THRESHOLD_TOKENS,
  a pre-compaction memory flush is triggered: a silent agent turn that writes durable
  memories to the sandbox before context is lost.
- Then a compaction LLM call summarizes everything up to the most recent messages.
- The summary is stored as a special "compaction" role message in the DB.
- ChatHistory.from_db_messages already handles compaction rows by truncating everything
  before the latest one and injecting the summary as context.

The result: old messages remain in the DB for audit/display purposes but are excluded
from future LLM context windows. The model always sees:
  [system prompt] + [compaction summary as context] + [recent messages since compaction]
"""
from typing import Optional

from core.config import Config
from utils.logger import get_logger

logger = get_logger(__name__)

_MEMORY_FLUSH_SYSTEM = (
    "Session nearing context compaction. "
    "Your job is to write any durable facts, decisions, or results to memory BEFORE context is lost."
)
_MEMORY_FLUSH_PROMPT = (
    "Before this session is compacted, save any lasting notes using bash:\n"
    "- Brief operational rules → append to MEMORY.md: echo \"- rule\" >> /home/user/MEMORY.md\n"
    "- Today's analysis notes → echo \"- note\" >> /home/user/memory/$(date +%%Y-%%m-%%d).md\n\n"
    "If there is nothing new worth persisting, call idle immediately. "
    "Do NOT reply to the user — this is a silent background operation."
)

_COMPACTION_SYSTEM_PROMPT = """You are summarizing a conversation between a user and an AI financial assistant called Finch.
Produce a dense, structured summary that preserves ALL of the following without loss:
- Every specific data point: numbers, percentages, dates, ticker symbols, dollar amounts
- File names and paths that were created or referenced
- Strategy names, parameters, and results
- Key decisions made and their rationale
- User preferences and instructions given
- Any errors encountered and how they were resolved
- Open questions or next steps mentioned

Format the summary as structured markdown. Use headers and bullet points. Be thorough — context lost here cannot be recovered.
"""

_COMPACTION_USER_PROMPT = """Summarize this conversation history. Preserve every specific fact, number, filename, and decision.

{history_text}

Write a comprehensive structured summary that a future session can use as complete context."""


async def _run_memory_flush(chat_id: str, user_id: str, skill_ids: list, db) -> None:
    """
    Silent agent turn that writes durable memories to the sandbox before compaction.

    The agent is given recent context, told this is a background operation, and
    should call memory_write for any lasting facts then call idle.
    The user never sees this turn — we consume the stream and discard events.
    """
    from crud import chat_async
    from schemas.chat_history import ChatHistory
    from modules.agent.agent_config import create_agent
    from modules.agent.context import AgentContext, generate_agent_id

    logger.info(f"Memory flush triggered for chat {chat_id} before compaction")

    try:
        # Load the current (large) history so the agent has context to work from
        db_messages = await chat_async.get_chat_messages(db, chat_id)
        chat_history = ChatHistory.from_db_messages(db_messages, chat_id, user_id)

        agent_id = generate_agent_id()
        context = AgentContext(
            user_id=user_id,
            chat_id=chat_id,
            agent_id=agent_id,
            skill_ids=skill_ids or [],
        )

        agent = await create_agent(context, user_id=user_id, skill_ids=skill_ids or [])

        # Append flush instructions to system prompt without changing the base prompt
        agent.system_prompt = agent.system_prompt + "\n\n" + _MEMORY_FLUSH_SYSTEM

        # Consume the entire stream silently — we don't save messages or yield events
        async for _ in agent.process_message_stream(
            message=_MEMORY_FLUSH_PROMPT,
            chat_history=chat_history,
            history_limit=30,
        ):
            pass

        logger.info(f"Memory flush complete for chat {chat_id}")
    except Exception as exc:
        logger.warning(f"Memory flush failed (non-fatal) for chat {chat_id}: {exc}")


async def maybe_compact(
    chat_id: str,
    user_id: str,
    db,
    skill_ids: Optional[list] = None,
) -> bool:
    """
    Check if the chat history needs compaction and run it if so.

    Before compacting, runs a silent memory flush turn so the agent can write
    durable facts to the sandbox before the context window is truncated.

    Returns True if compaction was performed, False otherwise.
    """
    if not Config.COMPACTION_ENABLED:
        return False

    from crud import chat_async
    from schemas.chat_history import ChatHistory

    db_messages = await chat_async.get_chat_messages(db, chat_id)
    if not db_messages:
        return False

    history = ChatHistory.from_db_messages(db_messages, chat_id, user_id)
    stats = history.get_statistics()
    estimated_tokens = stats["estimated_tokens"]

    if estimated_tokens < Config.COMPACTION_THRESHOLD_TOKENS:
        return False

    logger.info(
        f"Compaction triggered for chat {chat_id}: "
        f"~{estimated_tokens:,} tokens (threshold: {Config.COMPACTION_THRESHOLD_TOKENS:,})"
    )

    # Fire memory flush before losing context — agent writes lasting facts to sandbox
    await _run_memory_flush(chat_id, user_id, skill_ids or [], db)

    summary = await _run_compaction(history)
    if not summary:
        logger.warning(f"Compaction LLM call returned empty summary for chat {chat_id}")
        return False

    # Persist the compaction summary as a special DB row.
    # Messages older than this row are excluded from future context loads.
    sequence = await chat_async.get_next_sequence(db, chat_id)
    await chat_async.create_message(
        db=db,
        chat_id=chat_id,
        role="compaction",
        content=summary,
        sequence=sequence,
    )

    logger.info(f"Compaction complete for chat {chat_id} (seq={sequence})")
    return True


async def _run_compaction(history) -> Optional[str]:
    """Call the LLM to produce a compaction summary. Returns the summary text."""
    from modules.agent.llm_handler import LLMHandler

    history_text = history.to_markdown(
        title="Conversation to Summarize",
        include_system=False,
        include_tool_results=True,
        max_tool_result_length=2000,
    )

    messages = [
        {"role": "system", "content": _COMPACTION_SYSTEM_PROMPT},
        {"role": "user", "content": _COMPACTION_USER_PROMPT.format(history_text=history_text)},
    ]

    handler = LLMHandler(user_id=None, chat_id=None, agent_type="compactor")

    try:
        response = await handler.acompletion(
            model=Config.COMPACTION_MODEL,
            messages=messages,
            stream=False,
            max_tokens=4096,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Compaction LLM call failed: {e}")
        return None
