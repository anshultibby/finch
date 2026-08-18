"""
Chat Logger - Simple conversation logging

Just saves what we send to Claude and what we get back. Debug-only: every
caller gates on Config.DEBUG_CHAT_LOGS.

Directory structure:
- chat_logs/{date}/{HHMMSS}_{chat_id}/master/conversation.json
- chat_logs/{date}/{HHMMSS}_{chat_id}/executors/{agent_id}/conversation.json

The datetime prefix ensures chronological ordering when browsing folders.
"""
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from datetime import datetime
import json
import re
from utils.logger import get_logger

logger = get_logger(__name__)

# chat_id / agent_id become path segments, so they must not be able to escape
# the chat_logs tree or produce names the filesystem rejects.
_SAFE_ID = re.compile(r"[^A-Za-z0-9._-]")

# Directory names are {HHMMSS}_{chat_id}. Only strip a prefix that is exactly
# six digits, otherwise a legacy dir named after a chat_id containing an
# underscore gets its first segment eaten.
_TIMESTAMP_PREFIX = re.compile(r"^\d{6}_")

# Resolving a log dir scans the whole chat_logs tree. Cache it per process so
# that cost is paid once per (chat, agent) rather than once per LLM call.
_LOG_DIR_CACHE: Dict[Tuple[str, str, Optional[str]], Path] = {}


def _sanitize_id(value: str, kind: str) -> str:
    """Reduce an externally-supplied id to something safe as a path segment."""
    safe = _SAFE_ID.sub("_", value or "")
    safe = safe.strip(".")
    if not safe:
        raise ValueError(f"{kind} is empty after sanitization: {value!r}")
    return safe


def _extract_chat_id_from_dir_name(dir_name: str) -> str:
    """
    Extract chat_id from directory name.
    Handles: {HHMMSS}_{chat_id} -> returns chat_id
             {chat_id} -> returns chat_id (legacy, incl. ids containing "_")
    """
    return _TIMESTAMP_PREFIX.sub("", dir_name, count=1)


def _agent_subdir(chat_dir: Path, agent_type: str, agent_id: Optional[str]) -> Path:
    if agent_type == "executor":
        if not agent_id:
            raise ValueError("agent_id is required for executor chat logs")
        return chat_dir / "executors" / _sanitize_id(agent_id, "agent_id")
    return chat_dir / "master"


def get_existing_log_dir(
    chat_id: str,
    backend_dir: Path,
    agent_type: str = "master",
    agent_id: str = None,
) -> Path | None:
    """
    Find the existing log directory for a chat_id, if one exists.

    Scans every date directory and returns the most recent match, so a chat
    that spans midnight (or a restart) resolves deterministically to its
    newest directory rather than to whatever iterdir() happened to yield first.

    Supports both new format ({HHMMSS}_{chat_id}) and legacy format ({chat_id}).

    Args:
        chat_id: The chat session ID
        backend_dir: Path to the backend directory
        agent_type: "master" or "executor"
        agent_id: Required for executor type, the agent's unique ID

    Returns:
        Path to existing log directory or None
    """
    chat_logs_dir = backend_dir / "chat_logs"
    if not chat_logs_dir.exists():
        return None

    target = _sanitize_id(chat_id, "chat_id")
    matches: List[Tuple[str, str, Path]] = []

    for date_dir in chat_logs_dir.iterdir():
        if not date_dir.is_dir():
            continue

        for chat_dir in date_dir.iterdir():
            if not chat_dir.is_dir():
                continue

            if _extract_chat_id_from_dir_name(chat_dir.name) == target:
                # Sort key is (date dir, dir name); both are zero-padded and
                # therefore sort lexicographically in chronological order.
                matches.append((date_dir.name, chat_dir.name, chat_dir))

    if not matches:
        return None

    matches.sort()
    return _agent_subdir(matches[-1][2], agent_type, agent_id)


def get_chat_log_dir(
    chat_id: str,
    backend_dir: Path,
    agent_type: str = "master",
    agent_id: str = None,
) -> Path:
    """
    Resolve the chat log directory for a given chat_id.

    Note this only computes a path -- the directory is created lazily by the
    first write.

    Directory structure:
    - Master: chat_logs/{date}/{HHMMSS}_{chat_id}/master/conversation.json
    - Executor: chat_logs/{date}/{HHMMSS}_{chat_id}/executors/{agent_id}/conversation.json

    If a directory already exists for this chat_id, it is reused.

    Args:
        chat_id: The chat session ID
        backend_dir: Path to the backend directory
        agent_type: "master" or "executor"
        agent_id: Required for executor type, the agent's unique ID

    Returns:
        Path to the chat log directory
    """
    cache_key = (chat_id, agent_type, agent_id)
    cached = _LOG_DIR_CACHE.get(cache_key)
    if cached is not None:
        return cached

    resolved = get_existing_log_dir(chat_id, backend_dir, agent_type, agent_id)

    if resolved is None:
        # No existing directory found - create a new one with current timestamp
        now = datetime.now()
        chat_dir_name = f"{now.strftime('%H%M%S')}_{_sanitize_id(chat_id, 'chat_id')}"
        base_dir = backend_dir / "chat_logs" / now.strftime("%Y%m%d") / chat_dir_name
        resolved = _agent_subdir(base_dir, agent_type, agent_id)

    _LOG_DIR_CACHE[cache_key] = resolved
    return resolved


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    """Read a jsonl file, skipping malformed lines rather than losing the file."""
    messages: List[Dict[str, Any]] = []
    skipped = 0
    with open(path, "r") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                messages.append(json.loads(line))
            except json.JSONDecodeError:
                skipped += 1
    if skipped:
        logger.warning(f"Skipped {skipped} malformed line(s) in {path.name}")
    return messages


class ChatLogger:
    """
    Chat logger - saves full conversation state with tool results.

    Structure:
    - conversation.json: Full conversation including tool results
    - messages.jsonl: Append-only message log for reconstructing history

    This logger captures the complete conversation cycle:
    1. User message
    2. Assistant message (with tool calls)
    3. Tool results
    4. Next assistant message
    """

    # Relative token pricing used only to report cache savings in the log.
    # Anthropic bills cache writes at 1.25x base input and cache reads at 0.1x.
    _RATE_INPUT = 1.0
    _RATE_CACHE_WRITE = 1.25
    _RATE_CACHE_READ = 0.1

    def __init__(self, user_id: str, chat_id: str, log_dir: Path, agent_type: str = "master", agent_id: str = None):
        self.user_id = user_id
        self.chat_id = chat_id
        self.agent_type = agent_type
        self.agent_id = agent_id
        self.log_dir = log_dir
        self.conversation_file = log_dir / "conversation.json"
        self.messages_file = log_dir / "messages.jsonl"

        # Model that is actually running this chat. Stamped as soon as it is
        # resolved (before the first LLM call) so a stream that crashes early
        # still records which model ran, instead of leaving model unknown.
        self.model: Optional[str] = None

        # In-memory message buffer for building complete conversation
        self._messages: List[Dict[str, Any]] = []

        # Turn-scoped metadata from the last full write. Kept so the cheap
        # per-message snapshots re-emit it instead of clobbering the file with
        # a stripped-down version.
        self._system_prompt: Optional[str] = None
        self._tools: Optional[List[Dict[str, Any]]] = None
        self._last_usage: Optional[Dict[str, Any]] = None
        self._cache_summary: Optional[Dict[str, Any]] = None

        # Load existing messages from file if it exists
        if self.messages_file.exists():
            try:
                self._messages = _load_jsonl(self.messages_file)
                logger.debug(f"📂 Loaded {len(self._messages)} messages from existing log")
            except Exception as e:
                logger.warning(f"Failed to load existing messages: {e}")
                self._messages = []

        # Load existing cache history from conversation file if it exists
        self.cache_history = []
        if self.conversation_file.exists():
            try:
                with open(self.conversation_file, "r") as f:
                    existing_data = json.load(f)
                self.cache_history = existing_data.get("cache_summary", {}).get("history", [])
                # Carry forward metadata already recorded by an earlier handler
                # for this chat (handlers share the same file).
                self.model = existing_data.get("model") or self.model
                self._system_prompt = existing_data.get("system_prompt")
                self._tools = existing_data.get("tools")
                self._last_usage = existing_data.get("last_usage")
                self._cache_summary = existing_data.get("cache_summary")
            except Exception as e:
                logger.warning(f"Failed to load existing cache history: {e}")
                self.cache_history = []

    def add_message(self, message: Dict[str, Any], update_snapshot: bool = True):
        """
        Add a single message to the log (append-only).

        Args:
            message: Message dict with role, content, etc.
            update_snapshot: Whether to update the conversation.json snapshot
        """
        # Add timestamp for tracking
        message_with_time = {
            **message,
            "logged_at": datetime.now().astimezone().isoformat()
        }

        self._messages.append(message_with_time)

        # Append to jsonl file immediately (append-only, always safe)
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            with open(self.messages_file, "a") as f:
                f.write(json.dumps(message_with_time) + "\n")
        except Exception as e:
            logger.error(f"Failed to append message to log: {e}")

        # Update conversation snapshot if requested
        if update_snapshot:
            self._write_conversation_file()

    def add_tool_results(self, tool_messages: List[Dict[str, Any]]):
        """
        Add tool result messages after assistant message with tool calls.

        Args:
            tool_messages: List of tool result messages
        """
        for msg in tool_messages:
            # Don't update snapshot on each message, we'll do one update at the end
            self.add_message(msg, update_snapshot=False)

        # Update snapshot once after all tool results are added
        self._write_conversation_file()

        logger.info(f"💾 Added {len(tool_messages)} tool result messages to conversation log")

    def log_llm_turn(
        self,
        assistant_response: Dict[str, Any],
        usage_data: Optional[Dict[str, Any]] = None,
        model: str = "unknown",
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None
    ):
        """
        Log a complete LLM turn including the assistant response.

        This should be called when the LLM finishes generating a response.
        The assistant message is added to the conversation.
        Tool results should be added separately via add_tool_results().

        Args:
            assistant_response: The assistant's response message
            usage_data: Token usage and cache stats for this turn
            model: Model name
            system_prompt: System prompt (Claude format, may be list of blocks)
            tools: Full tool definitions sent to LLM
        """
        # Append first so the turn/message counts include this response, then
        # fold in the metadata and write the file once.
        self.add_message(assistant_response, update_snapshot=False)
        self._record_turn_metadata(usage_data, model, system_prompt, tools)
        self._write_conversation_file()

    def _record_turn_metadata(
        self,
        usage_data: Optional[Dict[str, Any]],
        model: str,
        system_prompt: Optional[Any],
        tools: Optional[List[Dict[str, Any]]],
    ):
        """Fold this turn's metadata into the logger's persistent state."""
        # Prefer a concretely-known model; keep self.model as the source of
        # truth so quick snapshots written later stay consistent.
        if model and model != "unknown":
            self.model = model

        if isinstance(system_prompt, list):
            self._system_prompt = "\n".join([
                block.get("text", "")
                for block in system_prompt
                if block.get("type") == "text"
            ])
        elif system_prompt:
            self._system_prompt = system_prompt

        if tools:
            self._tools = tools

        if usage_data:
            self._last_usage = usage_data
            self._cache_summary = self._build_cache_summary(usage_data)

    def _write_conversation_file(self):
        """Write the full conversation snapshot file with all metadata."""
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)

            data = {
                "user_id": self.user_id,
                "chat_id": self.chat_id,
                "agent_type": self.agent_type,
                "agent_id": self.agent_id,
                "model": self.model or "unknown",
                "updated_at": datetime.now().astimezone().isoformat(),
                "system_prompt": self._system_prompt,
                "messages": self._messages,
                "message_count": len(self._messages),
            }

            if self._last_usage:
                data["last_usage"] = self._last_usage
            if self._cache_summary:
                data["cache_summary"] = self._cache_summary
            else:
                data["note"] = "Usage statistics unavailable in Claude streaming mode"
            if self._tools:
                data["tools"] = self._tools

            # Write conversation file atomically
            temp_file = self.conversation_file.with_suffix('.tmp')
            with open(temp_file, "w") as f:
                json.dump(data, f, indent=2)
            temp_file.replace(self.conversation_file)

        except Exception as e:
            logger.error(f"Failed to write conversation file: {e}", exc_info=True)

    def _turn_number(self) -> int:
        """Turn count = assistant messages so far (tool results don't add turns)."""
        return sum(1 for m in self._messages if m.get("role") == "assistant")

    def _cost(self, fresh: int, cache_write: int, cache_read: int) -> float:
        return (
            fresh * self._RATE_INPUT
            + cache_write * self._RATE_CACHE_WRITE
            + cache_read * self._RATE_CACHE_READ
        )

    def _build_cache_summary(self, usage_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Append this turn to cache history and rebuild the summary block."""
        cache_info = usage_data.get("cache", {})
        if not cache_info:
            return None

        total_input_tokens = usage_data.get("prompt_tokens", 0)
        cache_read_tokens = cache_info.get("read_tokens", 0)
        cache_creation_tokens = cache_info.get("creation_tokens", 0)
        # Tokens billed at full rate: everything neither read from nor written
        # to the cache.
        fresh_input_tokens = max(
            0, total_input_tokens - cache_read_tokens - cache_creation_tokens
        )

        full_price_cost = total_input_tokens * self._RATE_INPUT
        actual_cost = self._cost(fresh_input_tokens, cache_creation_tokens, cache_read_tokens)
        cost_savings_pct = (
            (full_price_cost - actual_cost) / full_price_cost * 100
        ) if full_price_cost > 0 else 0

        hit_rate = (
            cache_read_tokens / total_input_tokens * 100
        ) if total_input_tokens > 0 else 0

        this_turn = {
            "turn": self._turn_number(),
            "message_count": len(self._messages),
            "fresh_input_tokens": fresh_input_tokens,
            "cache_read_tokens": cache_read_tokens,
            "total_input_tokens": total_input_tokens,
            "cache_creation_tokens": cache_creation_tokens,
            "cache_hit": cache_info.get("cache_hit", False),
            "cache_hit_rate": f"{hit_rate:.1f}%",
            "cost_savings": f"{cost_savings_pct:.1f}%",
        }
        self.cache_history.append(this_turn)

        # Cumulative stats across every turn recorded for this chat
        def _sum(key: str) -> int:
            return sum(entry.get(key, 0) for entry in self.cache_history)

        total_written = _sum("cache_creation_tokens")
        total_input_all_turns = _sum("total_input_tokens")
        total_cache_read = _sum("cache_read_tokens")
        total_fresh = _sum("fresh_input_tokens")

        cumulative_full_cost = total_input_all_turns * self._RATE_INPUT
        cumulative_actual_cost = self._cost(total_fresh, total_written, total_cache_read)
        cumulative_savings_pct = (
            (cumulative_full_cost - cumulative_actual_cost) / cumulative_full_cost * 100
        ) if cumulative_full_cost > 0 else 0

        avg_hit_rate = (
            total_cache_read / total_input_all_turns * 100
        ) if total_input_all_turns > 0 else 0

        return {
            "explanation": {
                "fresh_input_tokens": "Tokens sent that were neither read from nor written to cache",
                "cache_creation_tokens": "NEW tokens being added to cache (billed at 1.25x)",
                "cache_read_tokens": "Tokens retrieved from cache (billed at 0.1x)",
                "why_different": "Not all new input is cached - only content at cache_control breakpoints",
            },
            "this_turn": this_turn,
            "cumulative": {
                "total_cache_tokens_written": total_written,
                "total_input_tokens_all_turns": total_input_all_turns,
                "total_cache_read_tokens": total_cache_read,
                "total_fresh_input_tokens": total_fresh,
                "avg_cache_hit_rate": f"{avg_hit_rate:.1f}%",
                "avg_cost_savings": f"{cumulative_savings_pct:.1f}%",
            },
            "history": self.cache_history,
        }
