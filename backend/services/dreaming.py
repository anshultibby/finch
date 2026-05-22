"""
Dreaming Service — post-chat reflection inspired by the brain's default mode network.

After a chat completes, this service runs a full agentic chat that:
1. Reads the agent's memory store and recent conversations using tools
2. Reflects on performance, patterns, and opportunities for improvement
3. Updates the store (learnings, strategy, modules, etc.) via tool calls
4. Produces artifacts like tested code modules or analysis templates

The dream runs as a real agent loop (with tool calls, bash access, etc.)
but does not create a visible chat record.
"""
import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from typing import Optional, List

from core.config import Config

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# In-memory event bus for dream progress streaming
# ---------------------------------------------------------------------------

class _DreamEventBus:
    """Stores all events for a dream and fans out to live subscribers.
    Late-connecting clients get a replay of all past events."""

    def __init__(self):
        self._buffers: dict[str, list[dict]] = {}
        self._subscribers: dict[str, list[asyncio.Queue]] = {}
        self._finished: dict[str, bool] = {}

    def init_dream(self, dream_id: str) -> None:
        self._buffers[dream_id] = []
        self._subscribers.setdefault(dream_id, [])
        self._finished[dream_id] = False

    async def emit(self, dream_id: str, event_type: str, data: dict) -> None:
        entry = {"event": event_type, "data": data}
        buf = self._buffers.get(dream_id)
        if buf is not None:
            buf.append(entry)
        subs = self._subscribers.get(dream_id, [])
        if event_type not in ("dream_thinking",):
            logger.debug(f"Dream event bus: {event_type} for {dream_id[:8]}, buffer={len(buf) if buf else 0}, subs={len(subs)}")
        for q in subs:
            try:
                await q.put(entry)
            except Exception:
                pass
        if event_type in ("dream_completed", "dream_failed"):
            self._finished[dream_id] = True

    def subscribe(self, dream_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        buf = self._buffers.get(dream_id, [])
        logger.info(f"Dream subscribe: {dream_id[:8]}, replaying {len(buf)} events, finished={self._finished.get(dream_id, 'no-entry')}")
        for past in buf:
            q.put_nowait(past)
        if self._finished.get(dream_id):
            q.put_nowait(None)
        else:
            self._subscribers.setdefault(dream_id, []).append(q)
        return q

    def unsubscribe(self, dream_id: str, q: asyncio.Queue) -> None:
        subs = self._subscribers.get(dream_id, [])
        if q in subs:
            subs.remove(q)

    def cleanup(self, dream_id: str) -> None:
        for q in self._subscribers.pop(dream_id, []):
            try:
                q.put_nowait(None)
            except Exception:
                pass
        self._buffers.pop(dream_id, None)
        self._finished.pop(dream_id, None)


_event_bus = _DreamEventBus()


def subscribe_dream(dream_id: str) -> asyncio.Queue:
    return _event_bus.subscribe(dream_id)


def unsubscribe_dream(dream_id: str, q: asyncio.Queue) -> None:
    _event_bus.unsubscribe(dream_id, q)


async def _emit_dream_event(dream_id: str, event_type: str, data: dict) -> None:
    await _event_bus.emit(dream_id, event_type, data)


# ---------------------------------------------------------------------------
# Phase detection from assistant text
# ---------------------------------------------------------------------------

_PHASE_PATTERNS = [
    (r"phase\s*1|replay|hippocampal", "replay"),
    (r"phase\s*2|simulate|constructive\s*episodic", "simulate"),
    (r"phase\s*3|mentalize|theory\s*of\s*mind", "mentalize"),
    (r"phase\s*4|connect|creative\s*association", "connect"),
    (r"phase\s*5|evaluate|value\s*estimation", "evaluate"),
    (r"phase\s*6|consolidate|memory\s*consolidation", "consolidate"),
]


def _detect_phase(text: str) -> Optional[str]:
    text_lower = text.lower()
    for pattern, phase in _PHASE_PATTERNS:
        if re.search(pattern, text_lower):
            return phase
    return None


# ---------------------------------------------------------------------------
# Dreaming system prompt (appended to the agent's normal system prompt)
# ---------------------------------------------------------------------------

DREAMING_SYSTEM_ADDENDUM = """\


<dreaming_mode>
You are now in DREAMING MODE. This is NOT a conversation with the user. You are \
alone with your memories — replaying, recombining, imagining, and consolidating.

This process is modeled on the brain's default mode network: the system that \
activates between tasks to replay experiences, simulate futures, model other \
agents, and forge connections across distant memories. Follow all six phases.

## Phase 1: REPLAY — Hippocampal Replay & Recombination

Read your store files (`ls /home/user/store/`, `cat /home/user/store/*.md`) and \
recent chat transcripts from `context/chats/`.

Do NOT just review conversations in order. After reading, actively look for:
- **Cross-conversation patterns** — themes, concerns, or questions that recur \
across sessions the user may not have connected themselves
- **Contradictions** — places where the user's stated preferences conflict with \
their actual behavior (e.g., says they want diversification but keeps adding tech)
- **Surprising overlaps** — a question from one conversation that sheds light on \
a completely different conversation

Write notable cross-links to `store/journal/` with today's date.

## Phase 2: SIMULATE — Constructive Episodic Simulation

Imagine 2-3 concrete future scenarios the user is likely to face based on what \
you know about their portfolio, interests, and current market conditions:
- What market events might affect their holdings in the next 1-4 weeks?
- What financial decisions are they approaching (earnings, rebalancing, tax events)?
- What might they ask you about next, and what data would you want ready?

For each scenario, write a brief anticipatory note to `store/anticipations.md` — \
what to watch for, what data to pull, what to proactively surface. Replace the \
file each dream (these are living predictions, not a log). Mark each with a date.

This is the medial temporal subsystem: constructing novel future scenes from \
stored fragments, not just reviewing the past.

## Phase 3: MENTALIZE — Theory of Mind & Self-Model

### User model
Go beyond surface preferences. Build a model of the user as an agent:
- What are their actual investment goals (not just stated — inferred from behavior)?
- What are they anxious about? What makes them engage vs. disengage?
- What are their blind spots — things they should be thinking about but aren't?
- What do their corrections and pushback reveal about their mental model?

Update `store/user_model.md` with concise bullet points. This file is your \
theory of mind — not "user likes tables" but "user is building conviction for \
a concentrated tech bet and wants data to stress-test it, not permission."

### Self-model
Reflect on your own patterns as Finch:
- Where do you tend to over-explain or under-deliver?
- What types of requests do you handle well vs. poorly?
- Are there recurring failure modes (wrong data, missed intent, slow responses)?

Update `store/self_model.md`. Keep it under 20 lines. This feeds future behavior.

## Phase 4: CONNECT — Creative Association

This is the divergent thinking phase. Cross-reference what you know about the \
user's holdings, interests, and questions with broader market and financial \
knowledge. Look for non-obvious connections:
- A holding in one sector that creates exposure to a risk discussed in another context
- A recurring question that points to an unmet need you could address differently
- Two separate interests that intersect (e.g., AI exposure + energy costs = data center REITs)

If you find a genuinely useful connection, write it to `store/insights.md` with \
a brief explanation. Keep only the 5-10 best insights. Prune aggressively — most \
associations are noise.

## Phase 5: EVALUATE — Value Estimation

Score the outputs from phases 2-4. Not everything you imagined or connected is \
worth keeping. For each item ask:
- Would this actually change what I say or do in the next conversation?
- Is this actionable or just interesting?
- Confidence level: am I speculating or is this grounded in data?

Delete low-value items. Promote high-value ones to `store/next_session.md` — \
a short list of things to proactively surface or check at the start of the next \
conversation. Replace this file each dream.

## Phase 6: CONSOLIDATE — Memory Consolidation

Now do the maintenance work:
- Extract user preferences and corrections from recent conversations → \
update `store/preferences.md`
- Extract actionable learnings from mistakes → update `store/learnings.md`
- Merge redundant entries across all store files
- Promote recurring journal patterns to preferences or learnings
- Remove stale or outdated notes
- Keep each file under ~50 lines. Concise is better.

Rate yourself 1-10 with brief justification.

## Rules
- USE YOUR TOOLS. Read and write files with bash.
- Keep all store files CONCISE. Bullet points, not paragraphs.
- Cross-link between pages using `[[page]]` wiki syntax (e.g., `see [[preferences]]`, \
`related to [[user_model]]`). The user sees these as clickable links.
- Be surgical with updates. Don't rewrite files that don't need it.
- Phases 1-5 are the novel DMN-inspired work. Phase 6 is maintenance. Spend most \
of your effort on 1-5 — that's where the value is.
- End with a brief summary of what you changed, top insight, and self-score (1-10).
- Do NOT attempt to message the user or take any external actions.
</dreaming_mode>
"""

DREAMING_USER_PROMPT = """\
Begin your dreaming session. Work through all six phases: REPLAY, SIMULATE, \
MENTALIZE, CONNECT, EVALUATE, CONSOLIDATE.

Start by reading your store contents and recent chat transcripts. After the \
review, spend most of your effort on simulation, mentalizing, and creative \
connections — the consolidation phase is important but the forward-looking \
phases are where the real value lives."""


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class DreamingService:
    """Manages dreaming sessions — full agentic chats for reflection."""

    async def trigger_dream(
        self,
        user_id: str,
        trigger_type: str = "post_chat",
        chat_ids: Optional[List[str]] = None,
    ) -> Optional[str]:
        """Create a dream record and launch background execution.
        Returns dream_id or None if skipped (cooldown/already running)."""
        if not Config.DREAMING_ENABLED:
            logger.debug("Dreaming disabled, skipping")
            return None

        from core.database import get_db_session
        from crud.store import get_running_dream, get_recent_dream, create_dream

        async with get_db_session() as db:
            running = await get_running_dream(db, user_id)
            if running:
                logger.debug(f"Dream already running for user {user_id}, skipping")
                return None

            recent = await get_recent_dream(db, user_id, Config.DREAMING_COOLDOWN_MINUTES)
            if recent:
                logger.debug(f"Dream ran recently for user {user_id}, skipping (cooldown)")
                return None

            dream = await create_dream(db, user_id, trigger_type, chat_ids)
            dream_id = str(dream.id)

        _event_bus.init_dream(dream_id)
        asyncio.create_task(self._execute_dream(dream_id, user_id, chat_ids or []))
        logger.info(f"Triggered dream {dream_id} for user {user_id} ({trigger_type})")
        return dream_id

    async def _execute_dream(
        self,
        dream_id: str,
        user_id: str,
        source_chat_ids: List[str],
    ) -> None:
        """Run the dream as a full agentic chat with tool access."""
        from core.database import get_db_session
        from crud.store import get_dream, update_dream
        from schemas.chat_history import ChatHistory
        from modules.agent.agent_config import create_agent
        from modules.agent.context import AgentContext, generate_agent_id

        started_at = datetime.now(timezone.utc)

        try:
            async with get_db_session() as db:
                dream = await get_dream(db, dream_id)
                if not dream:
                    return
                await update_dream(db, dream, status="running", started_at=started_at)

            agent_id = generate_agent_id()
            dream_chat_id = f"dream-{dream_id}"
            context = AgentContext(
                user_id=user_id,
                chat_id=dream_chat_id,
                agent_id=agent_id,
                skill_ids=[],
                data={},
            )

            agent = await create_agent(context, user_id=user_id, skill_ids=[])
            agent.system_prompt = agent.system_prompt + DREAMING_SYSTEM_ADDENDUM

            empty_history = ChatHistory(chat_id=dream_chat_id, user_id=user_id)
            empty_history.add_user_message(DREAMING_USER_PROMPT)

            last_assistant_content = ""
            streaming_text = ""
            output_diff = []
            seen_paths = set()
            transcript: List[dict] = [{"role": "user", "content": DREAMING_USER_PROMPT}]
            current_phase = None
            tool_count = 0

            await _emit_dream_event(dream_id, "dream_started", {
                "dream_id": dream_id, "phase": "starting",
            })
            logger.info(f"Dream {dream_id}: starting agent stream, subscribers={len(_event_bus._subscribers.get(dream_id, []))}")

            async for event in agent.process_message_stream(
                message=DREAMING_USER_PROMPT,
                chat_history=empty_history,
                history_limit=50,
            ):
                if event.event == "assistant_message_delta":
                    delta = event.data.get("delta", "")
                    streaming_text += delta
                    detected = _detect_phase(streaming_text)
                    if detected and detected != current_phase:
                        current_phase = detected
                        await _emit_dream_event(dream_id, "dream_phase", {
                            "dream_id": dream_id,
                            "phase": current_phase,
                        })
                    if len(streaming_text) % 200 < len(delta):
                        await _emit_dream_event(dream_id, "dream_thinking", {
                            "dream_id": dream_id,
                            "content": streaming_text[-500:],
                            "phase": current_phase,
                        })

                elif event.event == "message_end":
                    content = event.data.get("content", "")
                    if content:
                        last_assistant_content = content
                        transcript.append({"role": "assistant", "content": content})
                        await _emit_dream_event(dream_id, "dream_thinking", {
                            "dream_id": dream_id,
                            "content": content[:500],
                            "phase": current_phase,
                        })
                    streaming_text = ""

                elif event.event == "tool_call_start":
                    tool_name = event.data.get("tool_name", "")
                    if tool_name:
                        await _emit_dream_event(dream_id, "dream_tool", {
                            "dream_id": dream_id,
                            "tool_name": tool_name,
                            "tool_count": tool_count + 1,
                            "phase": current_phase,
                            "status": "running",
                        })

                elif event.event == "tools_end":
                    execution_results = event.data.get("execution_results", [])
                    for er in execution_results:
                        tool_name = er.get("tool_name", "")
                        tool_params = er.get("params", {})
                        tool_result = er.get("result", {})
                        result_str = json.dumps(tool_result, default=str) if isinstance(tool_result, dict) else str(tool_result)
                        tool_count += 1
                        transcript.append({
                            "role": "tool",
                            "tool_name": tool_name,
                            "input": self._truncate_tool_data(tool_params),
                            "output": result_str[:2000],
                        })

                        await _emit_dream_event(dream_id, "dream_tool", {
                            "dream_id": dream_id,
                            "tool_name": tool_name,
                            "tool_count": tool_count,
                            "phase": current_phase,
                            "status": "complete",
                        })

                        if tool_name in ("memory_write", "bash"):
                            target = tool_result.get("target", "") if isinstance(tool_result, dict) else ""
                            if target and "store/" in str(target):
                                is_new = target not in seen_paths
                                seen_paths.add(target)
                                content_written = tool_params.get("content", "")
                                lines_added = content_written.count("\n") + (1 if content_written else 0)
                                mode = tool_params.get("mode", "append")
                                diff_entry = {
                                    "path": str(target),
                                    "action": mode,
                                    "lines_added": lines_added,
                                    "lines_removed": 0 if mode == "append" else None,
                                    "is_new": is_new,
                                }
                                output_diff.append(diff_entry)
                                await _emit_dream_event(dream_id, "dream_file_write", {
                                    "dream_id": dream_id,
                                    "phase": current_phase,
                                    **diff_entry,
                                })

            summary = last_assistant_content[:2000] if last_assistant_content else "Dream completed"
            self_score = self._extract_score(last_assistant_content)

            async with get_db_session() as db:
                dream = await get_dream(db, dream_id)
                await update_dream(
                    db, dream,
                    status="completed",
                    summary=summary,
                    self_score=self_score,
                    output_diff=output_diff if output_diff else None,
                    transcript=transcript,
                    completed_at=datetime.now(timezone.utc),
                )

            await _emit_dream_event(dream_id, "dream_completed", {
                "dream_id": dream_id,
                "summary": summary[:300],
                "self_score": self_score,
                "files_changed": len(output_diff),
                "tool_count": tool_count,
            })

            logger.info(
                f"Dream {dream_id} completed: score={self_score}, "
                f"store_writes={len(output_diff)}"
            )

        except Exception as exc:
            logger.error(f"Dream {dream_id} failed: {exc}", exc_info=True)
            await _emit_dream_event(dream_id, "dream_failed", {
                "dream_id": dream_id,
                "error": str(exc)[:300],
            })
            try:
                async with get_db_session() as db:
                    dream = await get_dream(db, dream_id)
                    if dream:
                        await update_dream(
                            db, dream,
                            status="failed",
                            error=str(exc)[:2000],
                            completed_at=datetime.now(timezone.utc),
                        )
            except Exception:
                pass
        finally:
            await asyncio.sleep(5)
            _event_bus.cleanup(dream_id)

    @staticmethod
    def _truncate_tool_data(data: dict, max_len: int = 1000) -> dict:
        out = {}
        for k, v in data.items():
            s = str(v)
            out[k] = s[:max_len] + "..." if len(s) > max_len else s
        return out

    def _extract_score(self, text: str) -> Optional[int]:
        """Try to extract a self-score (1-10) from the agent's final message."""
        patterns = [
            r'(?:self[- ]?score|rating|score)[:\s]*(\d{1,2})\s*/\s*10',
            r'(\d{1,2})\s*/\s*10',
            r'(?:score|rating)[:\s]*(\d{1,2})\b',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                score = int(match.group(1))
                if 1 <= score <= 10:
                    return score
        return None
