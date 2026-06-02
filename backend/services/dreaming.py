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
    (r"step\s*1|read(?:ing)?(?:\s+all)?\s+store", "read"),
    (r"step\s*2|extract|organize|organiz", "organize"),
    (r"step\s*3|look\s*ahead|anticipat|next.session", "look-ahead"),
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
You are now in DREAMING MODE. This is NOT a conversation with the user.

Your job is to be a LIBRARIAN for the user's memory wiki. You process recent \
conversations, extract what matters, and organize it into a densely cross-linked \
wiki — like a personal Wikipedia about the user's financial life.

## Step 1: READ

Read all store files and recent chat transcripts:
```
ls /home/user/store/ && cat /home/user/store/*.md
ls /home/user/store/journal/ 2>/dev/null && cat /home/user/store/journal/*.md 2>/dev/null
ls /home/user/context/chats/ && cat /home/user/context/chats/*/*.md
```

As you read, note what's new: facts, decisions, corrections, positions, \
questions, mistakes.

## Step 2: ORGANIZE THE WIKI

Think like Wikipedia. Pages should be about **topics**, not categories. \
Don't shove everything into a few big files — create pages for whatever \
deserves its own page.

Examples of good page names:
- `VRDN.md` — everything known about this position: thesis, catalysts, risks, \
dates, what the user thinks about it
- `tax-loss-harvesting.md` — the user's approach, rules, past swaps
- `concentrated-positions.md` — the user's philosophy on concentration vs. \
diversification, how it shows up in their portfolio
- `binary-events.md` — pattern of how the user trades around PDUFA dates, \
earnings, etc.
- `communication-style.md` — how the user wants Finch to respond

Some pages will be about **stocks/positions**, some about **strategies**, \
some about **the user**, some about **Finch itself**. Let the content dictate \
the structure. Create a new page whenever a topic has enough substance to \
stand alone — don't wait for permission.

A few pages are special and should always exist:
- **next_session.md** — 2-3 things to proactively surface next conversation. \
Replace each dream.
- **journal/YYYY-MM-DD.md** — daily log of notable events and decisions.

For every page:
- **Bullet points**, not paragraphs. Keep pages under ~50 lines.
- **Deduplicate** and **prune** stale content.
- **Create new pages** when a topic outgrows its current location.
- **Split big pages** — if a page covers 3 distinct topics, make it 3 pages.

### Cross-linking — the most important part

A wiki without links is just a folder of files. Your job is to weave pages \
into a connected knowledge graph using `[[page]]` syntax.

Link aggressively:
- When a page mentions a stock that has its own page → `[[VRDN]]`
- When a strategy references the user's preferences → `[[communication-style]]`
- When a learning came from a specific position → `[[IMUX]]`
- When a journal entry records a decision about a strategy → `[[concentrated-positions]]`

Examples:
- `- Holding through PDUFA (see [[binary-events]], [[VRDN]])`
- `- User prefers stress-test framing over permission-seeking (see [[communication-style]])`
- `- Missed warrant dilution in analysis — see [[IMUX]], [[learnings]]`

Every page should link to at least 2 other pages. No orphans. After editing, \
ask: "could someone navigate the full picture by following links from any \
starting page?" If not, add more links.

## Step 3: LOOK AHEAD (brief)

After organizing, update `next_session.md` with 2-3 things to surface next \
conversation. If you spotted a non-obvious connection across topics, note it \
on the relevant page — don't create a separate insights dump.

## Rules
- USE YOUR TOOLS. Read and write files with bash.
- Spend ~80% of effort on Step 2 and ~20% on Step 3.
- The wiki's value is in its LINKS. The user sees `[[page]]` as clickable \
navigation in the UI. A well-linked wiki is the entire point.
- Create pages freely. There is no fixed schema — the wiki grows organically.
- Be surgical. Don't rewrite pages that don't need changes.
- Do NOT attempt to message the user or take any external actions.

## Final message (IMPORTANT)
Your LAST message is shown directly to the user as the dream summary. Make it \
a clear, readable recap of everything you did:
- Which chat transcripts you processed
- Pages created or updated (with brief note on what changed)
- New connections or insights you noticed
- What you put in next_session.md

Keep it concise but complete — this is the user's only window into what the \
dream accomplished.
</dreaming_mode>
"""

_DREAMING_USER_PROMPT_BASE = """\
Begin your dreaming session. Read your store and recent chat transcripts, then \
organize the wiki. Focus on extracting and filing new information from \
conversations, deduplicating, pruning stale entries, and cross-linking. \
After organizing, briefly update anticipations and next_session."""


def build_dreaming_user_prompt(last_dream_at: Optional[datetime] = None) -> str:
    if not last_dream_at:
        return _DREAMING_USER_PROMPT_BASE
    ts = last_dream_at.strftime("%Y-%m-%d %H:%M UTC")
    return (
        f"{_DREAMING_USER_PROMPT_BASE}\n\n"
        f"Your last dreaming session completed at {ts}. You must read chat "
        f"transcripts from AFTER that time — those haven't been processed yet. "
        f"You may also reference older transcripts if needed, but the new ones "
        f"are the priority."
    )


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
        from crud.store import get_running_dream, get_recent_dream, get_last_completed_dream, create_dream

        async with get_db_session() as db:
            running = await get_running_dream(db, user_id)
            if running:
                logger.debug(f"Dream already running for user {user_id}, skipping")
                return None

            if trigger_type != "manual":
                recent = await get_recent_dream(db, user_id, Config.DREAMING_COOLDOWN_MINUTES)
                if recent:
                    logger.debug(f"Dream ran recently for user {user_id}, skipping (cooldown)")
                    return None

            last_completed = await get_last_completed_dream(db, user_id)
            last_dream_at = last_completed.completed_at if last_completed else None

            dream = await create_dream(db, user_id, trigger_type, chat_ids)
            dream_id = str(dream.id)

        _event_bus.init_dream(dream_id)
        asyncio.create_task(self._execute_dream(dream_id, user_id, chat_ids or [], last_dream_at))
        logger.info(f"Triggered dream {dream_id} for user {user_id} ({trigger_type})")
        return dream_id

    async def _execute_dream(
        self,
        dream_id: str,
        user_id: str,
        source_chat_ids: List[str],
        last_dream_at: Optional[datetime] = None,
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

            pre_files = await self._snapshot_store_files(user_id)

            user_prompt = build_dreaming_user_prompt(last_dream_at)

            empty_history = ChatHistory(chat_id=dream_chat_id, user_id=user_id)
            empty_history.add_user_message(user_prompt)

            last_assistant_content = ""
            streaming_text = ""
            output_diff = []
            seen_paths = set()
            transcript: List[dict] = [{"role": "user", "content": user_prompt}]
            current_phase = None
            tool_count = 0

            await _emit_dream_event(dream_id, "dream_started", {
                "dream_id": dream_id, "phase": "starting",
            })
            logger.info(f"Dream {dream_id}: starting agent stream, subscribers={len(_event_bus._subscribers.get(dream_id, []))}")

            async for event in agent.process_message_stream(
                message=user_prompt,
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

            post_files = await self._snapshot_store_files(user_id)
            file_changes = self._compute_file_changes(pre_files, post_files)

            # Persist the dream's store writes to the DB (store_files table) NOW,
            # while the sandbox is still alive. The dream is the primary store
            # writer, so without this the consolidated memory never leaves the
            # sandbox before it idle-pauses and the Memory Store UI reads empty.
            try:
                from services.store_sync import sync_store_files
                await sync_store_files(user_id)
            except Exception as e:
                logger.warning(f"Store sync after dream failed for {user_id}: {e}")

            summary = last_assistant_content if last_assistant_content else "Dream completed"
            if file_changes:
                changes_section = "\n\n**Files changed:**\n" + "\n".join(
                    f"- {'+ ' if c['action'] == 'added' else '- ' if c['action'] == 'deleted' else '~ '}{c['path']}"
                    for c in file_changes
                )
                summary = summary + changes_section
            self_score = self._extract_score(last_assistant_content)

            async with get_db_session() as db:
                dream = await get_dream(db, dream_id)
                await update_dream(
                    db, dream,
                    status="completed",
                    summary=summary,
                    self_score=self_score,
                    output_diff=file_changes if file_changes else (output_diff if output_diff else None),
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

    @staticmethod
    async def _snapshot_store_files(user_id: str) -> dict[str, int]:
        """Return {relative_path: size} for all files in the user's store."""
        try:
            from modules.tools.implementations.code_execution import get_or_create_sandbox
            entry = await get_or_create_sandbox(user_id, envs={})
            entries = await entry.sbx.files.list("/home/user/store", depth=3)
            result = {}
            for e in entries:
                if hasattr(e, "type") and e.type == "dir":
                    continue
                name = e.name if hasattr(e, "name") else str(e)
                size = e.size if hasattr(e, "size") else 0
                result[name] = size
            return result
        except Exception as exc:
            logger.debug(f"Could not snapshot store files: {exc}")
            return {}

    @staticmethod
    def _compute_file_changes(
        before: dict[str, int], after: dict[str, int]
    ) -> List[dict]:
        changes = []
        for path in sorted(after.keys() - before.keys()):
            changes.append({"path": path, "action": "added"})
        for path in sorted(before.keys() - after.keys()):
            changes.append({"path": path, "action": "deleted"})
        for path in sorted(before.keys() & after.keys()):
            if before[path] != after[path]:
                changes.append({"path": path, "action": "modified"})
        return changes

    def _extract_score(self, text: str) -> Optional[int]:
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
