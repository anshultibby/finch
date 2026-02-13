"""
Chat History Models - Type-safe conversation management

Provides clean abstractions for managing chat history throughout the agent loop.
"""
from typing import List, Optional, Dict, Any, Literal, Tuple, Set, Union
from datetime import datetime
from pydantic import BaseModel, Field
import json
import logging

logger = logging.getLogger(__name__)


def _is_valid_tool_call_json(args: Any) -> bool:
    """Check if tool call arguments are valid JSON."""
    if isinstance(args, dict):
        return True
    if not args or not isinstance(args, str):
        return True
    try:
        json.loads(args)
        return True
    except json.JSONDecodeError:
        return False


def _sanitize_tool_calls(tool_calls: Optional[List[Dict[str, Any]]]) -> Tuple[List[Dict[str, Any]], Set[str]]:
    """
    Remove tool calls with malformed JSON arguments (from interrupted streams).
    Returns (valid_tool_calls, removed_tool_call_ids).
    """
    if not tool_calls:
        return [], set()
    
    valid = []
    removed_ids = set()
    
    for tc in tool_calls:
        tc_id = tc.get("id", "")
        args = tc.get("function", {}).get("arguments", "{}")
        
        if _is_valid_tool_call_json(args):
            valid.append(tc)
        else:
            logger.warning(f"Removing malformed tool call (id={tc_id}): truncated JSON")
            removed_ids.add(tc_id)
    
    return valid, removed_ids


class ToolCall(BaseModel):
    """Represents a tool call in a message"""
    id: str
    type: Literal["function"] = "function"
    function: Dict[str, Any]  # {name: str, arguments: str}


class ChatMessage(BaseModel):
    """
    Single message in conversation. Supports OpenAI format with multimodal content.
    
    Content can be:
    - str: Simple text
    - List[Dict]: Multimodal content blocks [{"type": "text", "text": "..."}, {"type": "image", ...}]
    """
    role: Literal["system", "user", "assistant", "tool"]
    content: Optional[Union[str, List[Dict[str, Any]]]] = None
    
    # Assistant messages with tool calls
    tool_calls: Optional[List[ToolCall]] = None
    
    # Tool result messages
    tool_call_id: Optional[str] = None
    name: Optional[str] = None
    
    # Metadata (not sent to LLM)
    sequence: Optional[int] = None
    timestamp: Optional[datetime] = None
    resource_id: Optional[str] = None
    
    def to_openai_format(self) -> Dict[str, Any]:
        """Convert to OpenAI/Anthropic API format."""
        msg = {"role": self.role}
        
        if self.content is not None:
            msg["content"] = self.content
        
        if self.tool_calls:
            msg["tool_calls"] = [tc.model_dump() for tc in self.tool_calls]
        
        if self.tool_call_id:
            msg["tool_call_id"] = self.tool_call_id
        
        if self.name:
            msg["name"] = self.name
        
        return msg
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChatMessage":
        """Create from dictionary (handles both raw dicts and parsed tool_calls)."""
        tool_calls = None
        if data.get("tool_calls"):
            tool_calls = [
                tc if isinstance(tc, ToolCall) else ToolCall(**tc)
                for tc in data["tool_calls"]
            ]
        
        # Parse JSON string content if needed
        content = data.get("content")
        if content and isinstance(content, str) and content.startswith('['):
            try:
                content = json.loads(content)
            except (json.JSONDecodeError, ValueError):
                pass
        
        return cls(
            role=data["role"],
            content=content,
            tool_calls=tool_calls,
            tool_call_id=data.get("tool_call_id"),
            name=data.get("name"),
            resource_id=data.get("resource_id"),
            sequence=data.get("sequence"),
            timestamp=data.get("timestamp"),
        )
    
    @classmethod
    def from_db(cls, db_row) -> "ChatMessage":
        """Create from database row."""
        content = db_row.content
        if content and isinstance(content, str) and content.startswith('['):
            try:
                content = json.loads(content)
            except (json.JSONDecodeError, ValueError):
                pass
        
        tool_calls = None
        if db_row.tool_calls:
            tool_calls = [ToolCall(**tc) for tc in db_row.tool_calls]
        
        return cls(
            role=db_row.role,
            content=content,
            tool_calls=tool_calls,
            tool_call_id=db_row.tool_call_id,
            name=db_row.name,
            resource_id=db_row.resource_id,
            sequence=db_row.sequence,
            timestamp=db_row.timestamp,
        )


class ChatHistory(BaseModel):
    """
    Manages conversation history with proper tool call/result pairing.
    
    Key invariant: Tool result messages must always follow their corresponding
    assistant message with tool_calls. The limit() method preserves this.
    """
    messages: List[ChatMessage] = Field(default_factory=list)
    chat_id: Optional[str] = None
    user_id: Optional[str] = None
    
    def add_message(self, message: ChatMessage) -> None:
        """Add a message, auto-assigning sequence if needed."""
        if message.sequence is None:
            message.sequence = len(self.messages)
        self.messages.append(message)
    
    def add_user_message(
        self, 
        content: Union[str, List[Dict[str, Any]]], 
        images: List[Dict[str, str]] = None
    ) -> None:
        """
        Add a user message (text or multimodal content).
        
        Args:
            content: Text string or list of content blocks
            images: Optional list of images [{"data": base64, "media_type": "image/png"}]
        """
        if images:
            # Convert to multimodal content format
            content_blocks = []
            if content:
                content_blocks.append({"type": "text", "text": content})
            for img in images:
                content_blocks.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": img.get("media_type", "image/png"),
                        "data": img["data"]
                    }
                })
            content = content_blocks
        
        self.add_message(ChatMessage(role="user", content=content))
    
    def to_openai_format(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Convert to OpenAI API format.
        
        If limit is specified, returns the most recent messages while preserving
        tool call/result pairs (never breaks a tool interaction in the middle).
        """
        if limit is None or limit <= 0 or limit >= len(self.messages):
            return [msg.to_openai_format() for msg in self.messages]
        
        # Smart limiting: find a safe cut point that doesn't break tool pairs
        messages = self.messages
        cut_index = len(messages) - limit
        
        # Scan forward from cut point to find a safe boundary
        # Safe boundaries: user message, or assistant message without pending tool results
        while cut_index < len(messages):
            msg = messages[cut_index]
            
            if msg.role == "user":
                break  # Safe to start from user message
            
            if msg.role == "assistant" and not msg.tool_calls:
                break  # Safe to start from assistant response (no tool calls)
            
            if msg.role == "assistant" and msg.tool_calls:
                # Check if all tool results are included after this point
                tool_ids = {tc.id for tc in msg.tool_calls}
                remaining = messages[cut_index + 1:]
                result_ids = {m.tool_call_id for m in remaining if m.role == "tool"}
                if tool_ids <= result_ids:
                    break  # All tool results are present, safe to include
            
            # Not safe, move forward
            cut_index += 1
        
        return [msg.to_openai_format() for msg in messages[cut_index:]]
    
    @classmethod
    def from_db_messages(cls, db_messages: List, chat_id: str, user_id: str) -> "ChatHistory":
        """
        Create from database messages with sanitization.
        
        Handles corruption from interrupted streams:
        - Removes malformed tool calls (truncated JSON from interrupted streams)
        - Removes orphaned tool results (whose tool_call was removed OR never saved)
        
        The key invariant for Anthropic API: every tool_result must have a matching
        tool_use in the immediately preceding assistant message.
        """
        history = cls(chat_id=chat_id, user_id=user_id)
        removed_tool_call_ids: Set[str] = set()
        
        # First pass: collect all valid tool_call IDs from assistant messages
        valid_tool_call_ids: Set[str] = set()
        temp_messages = []
        
        for db_msg in db_messages:
            msg_data = {
                "role": db_msg.role,
                "content": db_msg.content,
                "tool_call_id": db_msg.tool_call_id,
                "name": db_msg.name,
                "resource_id": db_msg.resource_id,
                "sequence": db_msg.sequence,
                "timestamp": db_msg.timestamp,
                "tool_calls": db_msg.tool_calls,
            }
            
            # Sanitize tool_calls and collect valid IDs
            if db_msg.role == "assistant" and db_msg.tool_calls:
                valid_tcs, removed = _sanitize_tool_calls(db_msg.tool_calls)
                removed_tool_call_ids.update(removed)
                msg_data["tool_calls"] = valid_tcs if valid_tcs else None
                
                # Track valid tool call IDs
                for tc in (valid_tcs or []):
                    tc_id = tc.get("id")
                    if tc_id:
                        valid_tool_call_ids.add(tc_id)
            
            temp_messages.append(msg_data)
        
        # Second pass: filter orphaned tool results
        # A tool result is orphaned if:
        # 1. Its tool_call_id was explicitly removed (malformed JSON)
        # 2. Its tool_call_id doesn't exist in ANY assistant message (chat was interrupted)
        orphaned_count = 0
        for msg_data in temp_messages:
            if msg_data["role"] == "tool":
                tool_call_id = msg_data.get("tool_call_id")
                if tool_call_id in removed_tool_call_ids:
                    logger.warning(f"Removing orphaned tool result (malformed tool_call): {tool_call_id}")
                    orphaned_count += 1
                    continue
                if tool_call_id and tool_call_id not in valid_tool_call_ids:
                    logger.warning(f"Removing orphaned tool result (missing tool_call): {tool_call_id}")
                    orphaned_count += 1
                    continue
            history.add_message(ChatMessage.from_dict(msg_data))
        
        if orphaned_count > 0:
            logger.info(f"Sanitized chat history: removed {orphaned_count} orphaned tool result(s)")
        
        return history
    
    def __len__(self) -> int:
        return len(self.messages)
    
    def __getitem__(self, index) -> ChatMessage:
        return self.messages[index]
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the chat history.
        
        Returns:
            Dictionary with statistics including message counts, character counts,
            token estimates, and tool call information.
        """
        stats = {
            "total_messages": len(self.messages),
            "by_role": {"user": 0, "assistant": 0, "tool": 0, "system": 0},
            "total_chars": 0,
            "estimated_tokens": 0,
            "tool_calls_count": 0,
            "tool_results_count": 0,
            "content_breakdown": {},
        }
        
        for msg in self.messages:
            # Count by role
            stats["by_role"][msg.role] = stats["by_role"].get(msg.role, 0) + 1
            
            # Count characters
            if msg.content:
                if isinstance(msg.content, str):
                    char_count = len(msg.content)
                elif isinstance(msg.content, list):
                    # Multimodal content - count text blocks only
                    char_count = sum(
                        len(block.get("text", "")) 
                        for block in msg.content 
                        if isinstance(block, dict) and block.get("type") == "text"
                    )
                else:
                    char_count = len(str(msg.content))
                
                stats["total_chars"] += char_count
                
                # Track content breakdown by role
                if msg.role not in stats["content_breakdown"]:
                    stats["content_breakdown"][msg.role] = {"chars": 0, "messages": 0}
                stats["content_breakdown"][msg.role]["chars"] += char_count
                stats["content_breakdown"][msg.role]["messages"] += 1
            
            # Count tool calls
            if msg.tool_calls:
                stats["tool_calls_count"] += len(msg.tool_calls)
                
                # Add character count for tool call arguments
                for tc in msg.tool_calls:
                    args = tc.function.get("arguments", "")
                    if isinstance(args, str):
                        stats["total_chars"] += len(args)
            
            # Count tool results
            if msg.role == "tool":
                stats["tool_results_count"] += 1
        
        # Estimate tokens (rough approximation: 4 chars per token)
        stats["estimated_tokens"] = stats["total_chars"] // 4
        
        return stats
    
    def print_statistics(self) -> None:
        """Print formatted statistics about the chat history."""
        stats = self.get_statistics()
        
        print("\n" + "="*60)
        print("CHAT HISTORY STATISTICS")
        print("="*60)
        print(f"Total Messages: {stats['total_messages']}")
        print(f"  - User:      {stats['by_role']['user']:>4}")
        print(f"  - Assistant: {stats['by_role']['assistant']:>4}")
        print(f"  - Tool:      {stats['by_role']['tool']:>4}")
        print(f"  - System:    {stats['by_role']['system']:>4}")
        print(f"\nTool Activity:")
        print(f"  - Tool Calls:   {stats['tool_calls_count']:>4}")
        print(f"  - Tool Results: {stats['tool_results_count']:>4}")
        print(f"\nContent Size:")
        print(f"  - Total Characters: {stats['total_chars']:>8,}")
        print(f"  - Estimated Tokens: {stats['estimated_tokens']:>8,}")
        print(f"\nContent Breakdown by Role:")
        for role, breakdown in stats['content_breakdown'].items():
            avg_chars = breakdown['chars'] // breakdown['messages'] if breakdown['messages'] > 0 else 0
            print(f"  - {role.capitalize():>9}: {breakdown['chars']:>8,} chars across {breakdown['messages']:>3} msgs (avg: {avg_chars:>6,} chars/msg)")
        print("="*60 + "\n")
    
    def to_markdown(
        self, 
        title: str = "Chat Transcript",
        include_system: bool = False,
        include_tool_results: bool = True,
        max_tool_result_length: int = 500
    ) -> str:
        """
        Convert chat history to a readable markdown transcript.
        
        Useful for:
        - Saving executor conversations for planner to review
        - Debugging/logging
        - Exporting conversations
        
        Args:
            title: Title for the transcript
            include_system: Whether to include system messages
            include_tool_results: Whether to include tool result content
            max_tool_result_length: Truncate tool results longer than this
        
        Returns:
            Markdown formatted string
        """
        lines = [f"# {title}", ""]
        
        for msg in self.messages:
            # Skip system messages unless requested
            if msg.role == "system" and not include_system:
                continue
            
            # Format based on role
            if msg.role == "user":
                lines.append("## User")
                content = self._extract_text_content(msg.content)
                lines.append(content)
                lines.append("")
            
            elif msg.role == "assistant":
                lines.append("## Assistant")
                
                # Add text content if present
                content = self._extract_text_content(msg.content)
                if content:
                    lines.append(content)
                
                # Add tool calls if present
                if msg.tool_calls:
                    lines.append("")
                    lines.append("**Tool Calls:**")
                    for tc in msg.tool_calls:
                        func_name = tc.function.get("name", "unknown")
                        args = tc.function.get("arguments", "{}")
                        # Parse and format args nicely
                        try:
                            if isinstance(args, str):
                                args_dict = json.loads(args)
                            else:
                                args_dict = args
                            # Show abbreviated args
                            args_preview = json.dumps(args_dict, indent=2)
                            if len(args_preview) > 200:
                                args_preview = args_preview[:200] + "..."
                        except:
                            args_preview = str(args)[:200]
                        
                        lines.append(f"- `{func_name}`: {args_preview}")
                
                lines.append("")
            
            elif msg.role == "tool" and include_tool_results:
                tool_name = msg.name or "unknown"
                content = self._extract_text_content(msg.content)
                
                # Truncate long tool results
                if len(content) > max_tool_result_length:
                    content = content[:max_tool_result_length] + f"... (truncated, {len(content)} chars total)"
                
                lines.append(f"**Tool Result ({tool_name}):**")
                lines.append(f"```")
                lines.append(content)
                lines.append(f"```")
                lines.append("")
        
        return "\n".join(lines)
    
    def _extract_text_content(self, content: Optional[Union[str, List[Dict[str, Any]]]]) -> str:
        """Extract text from content (handles both string and multimodal formats)."""
        if content is None:
            return ""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            # Multimodal content - extract text blocks
            texts = []
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        texts.append(block.get("text", ""))
                    elif block.get("type") == "image":
                        texts.append("[Image]")
            return "\n".join(texts)
        return str(content)
