"""
Chat Logger - Simple conversation logging

Just saves what we send to Claude and what we get back.
"""
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
import json
from utils.logger import get_logger

logger = get_logger(__name__)


def get_chat_log_dir(chat_id: str, backend_dir: Path) -> Path:
    """
    Get or create the chat log directory for a given chat_id.
    
    Directory structure: chat_logs/{date}/{timestamp}_{chat_id}/
    
    This function will:
    1. Look for an existing directory for this chat_id within today's date
    2. If found, return that directory (to continue logging to the same location)
    3. If not found, create a new directory with current timestamp
    
    Args:
        chat_id: The chat session ID
        backend_dir: Path to the backend directory
        
    Returns:
        Path to the chat log directory
    """
    date_str = datetime.now().strftime("%Y%m%d")
    date_dir = backend_dir / "chat_logs" / date_str
    
    # Look for existing directory for this chat_id
    if date_dir.exists():
        for dir_path in date_dir.iterdir():
            if dir_path.is_dir() and dir_path.name.endswith(f"_{chat_id}"):
                return dir_path
    
    # Create new directory with timestamp
    timestamp = datetime.now().strftime("%H%M%S")
    return date_dir / f"{timestamp}_{chat_id}"


class ChatLogger:
    """
    Simple chat logger - saves full conversation state on each turn.
    
    Structure:
    - conversation.json: Array of turns, each with full context + response + stats
    """
    
    def __init__(self, user_id: str, chat_id: str, log_dir: Path):
        self.user_id = user_id
        self.chat_id = chat_id
        self.log_dir = log_dir
        self.conversation_file = log_dir / "conversation.json"
        
        # Load existing cache history from conversation file if it exists
        self.cache_history = []  # Track cache growth over conversation
        if self.conversation_file.exists():
            try:
                with open(self.conversation_file, "r") as f:
                    existing_data = json.load(f)
                    cache_summary = existing_data.get("cache_summary", {})
                    self.cache_history = cache_summary.get("history", [])
                    logger.debug(f"📊 Loaded {len(self.cache_history)} cache history entries from existing conversation")
            except Exception as e:
                logger.warning(f"Failed to load existing cache history: {e}")
                self.cache_history = []
        
    def log_conversation(
        self,
        messages: List[Dict[str, Any]],
        usage_data: Optional[Dict[str, Any]] = None,
        model: str = "unknown",
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None
    ):
        """
        Save the current conversation state (replaces file each time).
        
        Args:
            messages: Current full conversation (what's being sent to Claude)
            usage_data: Token usage and cache stats for this turn
            model: Model name
            system_prompt: System prompt (Claude format, may be list of blocks)
            tools: Full tool definitions sent to LLM (OpenAI format) - saved to logs
        """
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

