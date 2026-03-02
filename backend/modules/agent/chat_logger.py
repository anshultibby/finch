"""
Chat Logger - Simple conversation logging

Just saves what we send to Claude and what we get back.

Directory structure:
- chat_logs/{date}/{HHMMSS}_{chat_id}/master/conversation.json
- chat_logs/{date}/{HHMMSS}_{chat_id}/executors/{agent_id}/conversation.json

The datetime prefix ensures chronological ordering when browsing folders.
"""
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
import json
from utils.logger import get_logger

logger = get_logger(__name__)


def get_chat_log_dir(chat_id: str, backend_dir: Path, agent_type: str = "master", agent_id: str = None) -> Path:
    """
    Get or create the chat log directory for a given chat_id.
    
    Directory structure:
    - Master: chat_logs/{date}/{datetime}_{chat_id}/master/conversation.json
    - Executor: chat_logs/{date}/{datetime}_{chat_id}/executors/{agent_id}/conversation.json
    
    If a directory already exists for this chat_id, it will be reused.
    
    Args:
        chat_id: The chat session ID
        backend_dir: Path to the backend directory
        agent_type: "master" or "executor"
        agent_id: Required for executor type, the agent's unique ID
        
    Returns:
        Path to the chat log directory
    """
    # First, check if an existing directory exists for this chat
    existing_dir = get_existing_log_dir(chat_id, backend_dir, agent_type, agent_id)
    if existing_dir:
        return existing_dir
    
    # No existing directory found - create a new one with current timestamp
    now = datetime.now()
    date_str = now.strftime("%Y%m%d")
    datetime_str = now.strftime("%H%M%S")
    chat_dir_name = f"{datetime_str}_{chat_id}"
    base_dir = backend_dir / "chat_logs" / date_str / chat_dir_name
    
    if agent_type == "executor":
        if not agent_id:
            raise ValueError("agent_id is required for executor chat logs")
        return base_dir / "executors" / agent_id
    else:
        return base_dir / "master"


def _extract_chat_id_from_dir_name(dir_name: str) -> str:
    """
    Extract chat_id from directory name.
    Handles: {HHMMSS}_{chat_id} -> returns chat_id
             {chat_id} -> returns chat_id
    """
    if "_" in dir_name:
        # Format: {timestamp}_{chat_id}
        parts = dir_name.split("_")
        # The chat_id is everything after the first underscore
        return "_".join(parts[1:])
    return dir_name


def get_existing_log_dir(chat_id: str, backend_dir: Path, agent_type: str = "master", agent_id: str = None) -> Path | None:
    """
    Find existing log directory for a chat_id if it exists.
    Searches through all date directories - returns ANY existing directory for this chat_id,
    regardless of timestamp. The timestamp is only for initial sorting, not for creating multiple dirs.
    
    Supports both new format ({datetime}_{chat_id}) and legacy format ({chat_id}).
    
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
    
    for date_dir in chat_logs_dir.iterdir():
        if not date_dir.is_dir():
            continue
        
        # Search for chat directory - could be new format (datetime_chat_id) or legacy (chat_id)
        for chat_dir in date_dir.iterdir():
            if not chat_dir.is_dir():
                continue
            
            # Extract the chat_id from the directory name (ignore timestamp prefix)
            dir_chat_id = _extract_chat_id_from_dir_name(chat_dir.name)
            
            # Check if this directory belongs to the chat we're looking for
            if dir_chat_id == chat_id:
                if agent_type == "executor":
                    if not agent_id:
                        raise ValueError("agent_id is required for executor chat logs")
                    return chat_dir / "executors" / agent_id
                else:
                    return chat_dir / "master"
    
    return None


def get_existing_master_log_dir(chat_id: str, backend_dir: Path) -> Path | None:
    """
    Find existing master log directory for a chat_id if it exists.
    Searches through all date directories and returns the MOST RECENT one.
    
    Supports both new format ({datetime}_{chat_id}) and legacy format ({chat_id}).
    
    Args:
        chat_id: The chat session ID
        backend_dir: Path to the backend directory
        
    Returns:
        Path to existing master log directory or None
    """
    return get_existing_log_dir(chat_id, backend_dir, agent_type="master")


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
    
    def __init__(self, user_id: str, chat_id: str, log_dir: Path, agent_type: str = "master", agent_id: str = None):
        self.user_id = user_id
        self.chat_id = chat_id
        self.agent_type = agent_type
        self.agent_id = agent_id
        self.log_dir = log_dir
        self.conversation_file = log_dir / "conversation.json"
        self.messages_file = log_dir / "messages.jsonl"
        
        # In-memory message buffer for building complete conversation
        self._messages: List[Dict[str, Any]] = []
        
        # Load existing messages from file if it exists
        if self.messages_file.exists():
            try:
                with open(self.messages_file, "r") as f:
                    self._messages = [json.loads(line) for line in f if line.strip()]
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
                    cache_summary = existing_data.get("cache_summary", {})
                    self.cache_history = cache_summary.get("history", [])
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
            "logged_at": datetime.now().isoformat()
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
            self._write_conversation_snapshot()
    
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
        self._write_conversation_snapshot()
        
        logger.info(f"💾 Added {len(tool_messages)} tool result messages to conversation log")
    
    def log_llm_turn(
        self,
        llm_input_messages: List[Dict[str, Any]],
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
            llm_input_messages: Messages sent to LLM (for reference)
            assistant_response: The assistant's response message
            usage_data: Token usage and cache stats for this turn
            model: Model name
            system_prompt: System prompt (Claude format, may be list of blocks)
            tools: Full tool definitions sent to LLM
        """
        # Add the assistant response to our message log
        self.add_message(assistant_response)
        
        # Update the conversation snapshot file
        self._write_conversation_file(
            messages=self._messages.copy(),
            usage_data=usage_data,
            model=model,
            system_prompt=system_prompt,
            tools=tools
        )
    
    def _write_conversation_snapshot(self):
        """
        Write a quick conversation snapshot with current messages.
        Used for continuous saving during the conversation.
        """
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            
            # Build minimal conversation snapshot
            data = {
                "user_id": self.user_id,
                "chat_id": self.chat_id,
                "agent_type": self.agent_type,
                "agent_id": self.agent_id,
                "updated_at": datetime.now().isoformat(),
                "messages": self._messages,
                "message_count": len(self._messages)
            }
            
            # Include cache summary if we have it
            if self.cache_history:
                data["cache_summary"] = {"history": self.cache_history}
            
            # Write conversation file atomically
            temp_file = self.conversation_file.with_suffix('.tmp')
            with open(temp_file, "w") as f:
                json.dump(data, f, indent=2)
            temp_file.replace(self.conversation_file)
            
        except Exception as e:
            logger.error(f"Failed to write conversation snapshot: {e}")
    
    def _write_conversation_file(
        self,
        messages: List[Dict[str, Any]],
        usage_data: Optional[Dict[str, Any]] = None,
        model: str = "unknown",
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None
    ):
        """Write the full conversation snapshot file with all metadata."""
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            
            # Extract system prompt text
            system_content = None
            if isinstance(system_prompt, list):
                system_content = "\n".join([
                    block.get("text", "") 
                    for block in system_prompt 
                    if block.get("type") == "text"
                ])
            elif system_prompt:
                system_content = system_prompt
            
            # Build conversation snapshot
            data = {
                "user_id": self.user_id,
                "chat_id": self.chat_id,
                "agent_type": self.agent_type,
                "agent_id": self.agent_id,
                "model": model,
                "updated_at": datetime.now().isoformat(),
                "system_prompt": system_content,
                "messages": messages,
                "message_count": len(messages)
            }
            
            # Add usage data
            if usage_data:
                data["last_usage"] = usage_data
                self._update_cache_stats(data, usage_data, messages)
            
            if tools:
                data["tools"] = tools
            
            # Write conversation file atomically
            temp_file = self.conversation_file.with_suffix('.tmp')
            with open(temp_file, "w") as f:
                json.dump(data, f, indent=2)
            temp_file.replace(self.conversation_file)
            
            logger.info(f"💾 Saved conversation snapshot ({len(messages)} messages)")
            
        except Exception as e:
            logger.error(f"Failed to write conversation file: {e}", exc_info=True)
    
    def _update_cache_stats(self, data: Dict, usage_data: Dict, messages: List):
        """Update cache statistics in the conversation data."""
        cache_info = usage_data.get("cache", {})
        if not cache_info:
            data["note"] = "Usage statistics unavailable in Claude streaming mode"
            return
        
        turn_number = len(messages) // 2
        
        total_input_tokens = usage_data.get("prompt_tokens", 0)
        cache_read_tokens = cache_info.get("read_tokens", 0)
        cache_creation_tokens = cache_info.get("creation_tokens", 0)
        new_input_tokens = cache_creation_tokens + (total_input_tokens - cache_read_tokens - cache_creation_tokens)
        
        full_price_cost = total_input_tokens * 1.0
        actual_cost = new_input_tokens * 1.0 + cache_read_tokens * 0.1
        cost_savings_pct = ((full_price_cost - actual_cost) / full_price_cost * 100) if full_price_cost > 0 else 0
        
        cache_entry = {
            "turn": turn_number,
            "message_count": len(messages),
            "new_input_tokens": new_input_tokens,
            "cache_read_tokens": cache_read_tokens,
            "total_input_tokens": total_input_tokens,
            "cache_creation_tokens": cache_info.get("creation_tokens", 0),
            "cache_hit": cache_info.get("cache_hit", False),
            "cache_hit_rate": f"{(cache_read_tokens / total_input_tokens * 100) if total_input_tokens > 0 else 0:.1f}%",
            "cost_savings": f"{cost_savings_pct:.1f}%"
        }
        self.cache_history.append(cache_entry)
        
        # Calculate cumulative stats
        total_cache_size = sum(entry["cache_creation_tokens"] for entry in self.cache_history)
        total_input_all_turns = sum(entry["total_input_tokens"] for entry in self.cache_history)
        total_cache_read_all_turns = sum(entry["cache_read_tokens"] for entry in self.cache_history)
        total_new_tokens = sum(entry["new_input_tokens"] for entry in self.cache_history)
        cumulative_full_cost = total_input_all_turns * 1.0
        cumulative_actual_cost = total_new_tokens * 1.0 + total_cache_read_all_turns * 0.1
        cumulative_savings_pct = ((cumulative_full_cost - cumulative_actual_cost) / cumulative_full_cost * 100) if cumulative_full_cost > 0 else 0
        
        data["cache_summary"] = {
            "explanation": {
                "new_input_tokens": "Tokens sent that weren't in cache",
                "cache_creation_tokens": "NEW tokens being added to cache",
                "cache_read_tokens": "Tokens retrieved from cache",
                "why_different": "Not all new input is cached - only content at cache_control breakpoints"
            },
            "this_turn": {
                "new_input_tokens": new_input_tokens,
                "cache_read_tokens": cache_read_tokens,
                "total_input_tokens": total_input_tokens,
                "cache_creation_tokens": cache_info.get("creation_tokens", 0),
                "cache_hit": cache_info.get("cache_hit", False),
                "cache_hit_rate": f"{(cache_read_tokens / total_input_tokens * 100) if total_input_tokens > 0 else 0:.1f}%",
                "cost_savings": f"{cost_savings_pct:.1f}%"
            },
            "cumulative": {
                "total_cache_size": total_cache_size,
                "total_input_tokens_all_turns": total_input_all_turns,
                "total_cache_read_tokens": total_cache_read_all_turns,
                "total_new_input_tokens": total_new_tokens,
                "avg_cache_hit_rate": f"{(total_cache_read_all_turns / total_input_all_turns * 100) if total_input_all_turns > 0 else 0:.1f}%",
                "avg_cost_savings": f"{cumulative_savings_pct:.1f}%"
            },
            "history": self.cache_history
        }
    
    def log_conversation(
        self,
        messages: List[Dict[str, Any]],
        usage_data: Optional[Dict[str, Any]] = None,
        model: str = "unknown",
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None
    ):
        """
        Legacy method: Save the current conversation state.
        
        This method replaces all messages with the provided list.
        For new code, prefer using add_message() and log_llm_turn().
        
        Args:
            messages: Current full conversation
            usage_data: Token usage and cache stats
            model: Model name
            system_prompt: System prompt
            tools: Tool definitions
        """
        self._messages = messages
        self._write_conversation_file(messages, usage_data, model, system_prompt, tools)
        try:
            # Create log directory if needed
            self.log_dir.mkdir(parents=True, exist_ok=True)
            
            # Extract system prompt text
            system_content = None
            if isinstance(system_prompt, list):
                # Claude format with cache control
                system_content = "\n".join([
                    block.get("text", "") 
                    for block in system_prompt 
                    if block.get("type") == "text"
                ])
            elif system_prompt:
                system_content = system_prompt
            
            # Build conversation snapshot
            data = {
                "user_id": self.user_id,
                "chat_id": self.chat_id,
                "model": model,
                "updated_at": datetime.now().isoformat(),
                "system_prompt": system_content,
                "messages": messages,
                "message_count": len(messages)
            }
            
            # Add usage data from this turn (if available)
            if usage_data:
                data["last_usage"] = usage_data
                
                # Track cache growth over time
                cache_info = usage_data.get("cache", {})
                if cache_info:
                    turn_number = len(messages) // 2  # Approximate turn number
                    
                    # According to Anthropic docs:
                    # - prompt_tokens = TOTAL input tokens
                    # - cache_read_input_tokens = tokens from cache
                    # - cache_creation_input_tokens = tokens being written to cache
                    # - input_tokens (in detailed response) = tokens AFTER last breakpoint
                    # Formula: prompt_tokens = cache_read + cache_creation + input_tokens
                    total_input_tokens = usage_data.get("prompt_tokens", 0)
                    cache_read_tokens = cache_info.get("read_tokens", 0)
                    cache_creation_tokens = cache_info.get("creation_tokens", 0)
                    # Actual new input = cache creation + input tokens after breakpoint
                    new_input_tokens = cache_creation_tokens + (total_input_tokens - cache_read_tokens - cache_creation_tokens)
                    
                    # Calculate cost savings
                    # Cache reads cost 10% of normal tokens, creation costs 25% more
                    full_price_cost = total_input_tokens * 1.0  # What we'd pay without cache
                    actual_cost = new_input_tokens * 1.0 + cache_read_tokens * 0.1  # What we actually pay
                    cost_savings_pct = ((full_price_cost - actual_cost) / full_price_cost * 100) if full_price_cost > 0 else 0
                    
                    cache_entry = {
                        "turn": turn_number,
                        "message_count": len(messages),
                        "new_input_tokens": new_input_tokens,  # Actually new/uncached tokens
                        "cache_read_tokens": cache_read_tokens,  # Tokens from cache
                        "total_input_tokens": total_input_tokens,  # Total (as reported by API)
                        "cache_creation_tokens": cache_info.get("creation_tokens", 0),
                        "cache_hit": cache_info.get("cache_hit", False),
                        "cache_hit_rate": f"{(cache_read_tokens / total_input_tokens * 100) if total_input_tokens > 0 else 0:.1f}%",
                        "cost_savings": f"{cost_savings_pct:.1f}%"
                    }
                    self.cache_history.append(cache_entry)
                    
                    # Calculate cumulative stats
                    total_cache_size = sum(entry["cache_creation_tokens"] for entry in self.cache_history)
                    total_input_all_turns = sum(entry["total_input_tokens"] for entry in self.cache_history)
                    total_cache_read_all_turns = sum(entry["cache_read_tokens"] for entry in self.cache_history)
                    
                    # Calculate cumulative cost savings
                    total_new_tokens = sum(entry["new_input_tokens"] for entry in self.cache_history)
                    cumulative_full_cost = total_input_all_turns * 1.0
                    cumulative_actual_cost = total_new_tokens * 1.0 + total_cache_read_all_turns * 0.1
                    cumulative_savings_pct = ((cumulative_full_cost - cumulative_actual_cost) / cumulative_full_cost * 100) if cumulative_full_cost > 0 else 0
                    
                    data["cache_summary"] = {
                        "explanation": {
                            "new_input_tokens": "Tokens sent that weren't in cache (user message + uncached context)",
                            "cache_creation_tokens": "NEW tokens being added to cache (only content with cache_control breakpoints)",
                            "cache_read_tokens": "Tokens retrieved from cache (system + tools + cached messages)",
                            "why_different": "Not all new input is cached - only content at cache_control breakpoints"
                        },
                        "this_turn": {
                            "new_input_tokens": new_input_tokens,
                            "cache_read_tokens": cache_read_tokens,
                            "total_input_tokens": total_input_tokens,
                            "cache_creation_tokens": cache_info.get("creation_tokens", 0),
                            "cache_hit": cache_info.get("cache_hit", False),
                            "cache_hit_rate": f"{(cache_read_tokens / total_input_tokens * 100) if total_input_tokens > 0 else 0:.1f}%",
                            "cost_savings": f"{cost_savings_pct:.1f}%"
                        },
                        "cumulative": {
                            "total_cache_size": total_cache_size,
                            "total_input_tokens_all_turns": total_input_all_turns,
                            "total_cache_read_tokens": total_cache_read_all_turns,
                            "total_new_input_tokens": total_new_tokens,
                            "avg_cache_hit_rate": f"{(total_cache_read_all_turns / total_input_all_turns * 100) if total_input_all_turns > 0 else 0:.1f}%",
                            "avg_cost_savings": f"{cumulative_savings_pct:.1f}%"
                        },
                        "history": self.cache_history
                    }
            else:
                # Note: Claude streaming doesn't always include usage stats
                data["note"] = "Usage statistics unavailable in Claude streaming mode"
            
            # Add full tool definitions (sent to LLM)
            if tools:
                data["tools"] = tools
            
            # Replace file with current state
            with open(self.conversation_file, "w") as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"💾 Saved conversation ({len(messages)} messages)")
            
        except Exception as e:
            logger.error(f"Failed to log conversation: {e}", exc_info=True)

