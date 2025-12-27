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
        
        - Removes malformed tool calls (truncated JSON from interrupted streams)
        - Removes orphaned tool results (whose tool_call was removed)
        """
        history = cls(chat_id=chat_id, user_id=user_id)
        removed_tool_call_ids: Set[str] = set()
        
        # First pass: collect and sanitize
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
            
            # Sanitize tool_calls
            if db_msg.role == "assistant" and db_msg.tool_calls:
                valid_tcs, removed = _sanitize_tool_calls(db_msg.tool_calls)
                removed_tool_call_ids.update(removed)
                msg_data["tool_calls"] = valid_tcs if valid_tcs else None
            
            temp_messages.append(msg_data)
        
        # Second pass: filter orphaned tool results
        for msg_data in temp_messages:
            if msg_data["role"] == "tool":
                if msg_data.get("tool_call_id") in removed_tool_call_ids:
                    continue  # Skip orphaned tool result
            history.add_message(ChatMessage.from_dict(msg_data))
        
        return history
    
    def __len__(self) -> int:
        return len(self.messages)
    
    def __getitem__(self, index) -> ChatMessage:
        return self.messages[index]
