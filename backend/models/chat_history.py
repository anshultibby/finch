"""
Chat History Models - Type-safe conversation management

Provides clean abstractions for managing chat history throughout the agent loop.
"""
from typing import List, Optional, Dict, Any, Literal, Tuple, Set
from datetime import datetime
from pydantic import BaseModel, Field
import json
import logging

logger = logging.getLogger(__name__)


def _is_valid_tool_call_json(args: Any) -> bool:
    """Check if tool call arguments are valid JSON."""
    if isinstance(args, dict):
        return True  # Already parsed
    if not args or not isinstance(args, str):
        return True  # Empty/None is fine
    try:
        json.loads(args)
        return True
    except json.JSONDecodeError:
        return False


def _sanitize_tool_calls(tool_calls: Optional[List[Dict[str, Any]]]) -> Tuple[List[Dict[str, Any]], Set[str]]:
    """
    Remove tool calls with malformed JSON arguments.
    
    Returns (valid_tool_calls, set_of_removed_tool_call_ids).
    """
    if not tool_calls:
        return [], set()
    
    valid = []
    removed_ids = set()
    
    for tc in tool_calls:
        tc_id = tc.get("id", "")
        func = tc.get("function", {})
        func_name = func.get("name", "unknown")
        args = func.get("arguments", "{}")
        
        if _is_valid_tool_call_json(args):
            valid.append(tc)
        else:
            logger.warning(f"Removing malformed tool call '{func_name}' (id={tc_id}): truncated/invalid JSON")
            removed_ids.add(tc_id)
    
    return valid, removed_ids


class ToolCall(BaseModel):
    """Represents a tool call in a message"""
    id: str
    type: Literal["function"] = "function"
    function: Dict[str, Any]  # {name: str, arguments: str}


class ImageContent(BaseModel):
    """Image content for multimodal messages"""
    data: str  # Base64-encoded image data
    media_type: str = "image/png"  # MIME type


class ChatMessage(BaseModel):
    """
    Represents a single message in the conversation.
    
    Supports OpenAI message format with extensions for our use cases.
    """
    role: Literal["system", "user", "assistant", "tool"]
    content: Optional[str] = None
    
    # Multimodal support - images attached to user messages
    images: Optional[List[ImageContent]] = None
    
    # Assistant messages with tool calls
    tool_calls: Optional[List[ToolCall]] = None
    
    # Tool messages
    tool_call_id: Optional[str] = None
    name: Optional[str] = None  # Tool name for tool messages
    
    # Metadata (not sent to LLM, used for our tracking)
    timestamp: Optional[datetime] = Field(default_factory=datetime.now)
    resource_id: Optional[str] = None  # For tool results that created resources
    sequence: Optional[int] = None  # For database ordering
    
    def to_openai_format(self) -> Dict[str, Any]:
        """
        Convert to OpenAI API format (only fields the API expects).
        
        Handles multimodal messages for Claude:
        - Text-only: content is a string
        - With images: content is a list of content blocks
        
        Returns clean dict for LLM API calls.
        """
        message = {"role": self.role}
        
        # Handle multimodal content (images + text)
        if self.images and self.role == "user":
            content_blocks = []
            
            # Add text first if present
            if self.content:
                content_blocks.append({
                    "type": "text",
                    "text": self.content
                })
            
            # Add images (Claude format)
            for img in self.images:
                content_blocks.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": img.media_type,
                        "data": img.data
                    }
                })
            
            message["content"] = content_blocks
        elif self.content is not None:
            message["content"] = self.content
        
        if self.tool_calls:
            message["tool_calls"] = [tc.model_dump() for tc in self.tool_calls]
        
        if self.tool_call_id:
            message["tool_call_id"] = self.tool_call_id
        
        if self.name:
            message["name"] = self.name
        
        return message
    
    def to_db_format(self) -> Dict[str, Any]:
        """
        Convert to database format (all fields for persistence).
        
        Returns dict suitable for chat_crud operations.
        """
        return {
            "role": self.role,
            "content": self.content or "",
            "tool_calls": [tc.model_dump() for tc in self.tool_calls] if self.tool_calls else None,
            "tool_call_id": self.tool_call_id,
            "name": self.name,
            "resource_id": self.resource_id,
            "sequence": self.sequence,
            "timestamp": self.timestamp
        }
    
    @classmethod
    def from_db(cls, db_message) -> "ChatMessage":
        """Create ChatMessage from database row"""
        return cls(
            role=db_message.role,
            content=db_message.content,
            tool_calls=[ToolCall(**tc) for tc in db_message.tool_calls] if db_message.tool_calls else None,
            tool_call_id=db_message.tool_call_id,
            name=db_message.name,
            resource_id=db_message.resource_id,
            sequence=db_message.sequence,
            timestamp=db_message.timestamp
        )
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChatMessage":
        """Create ChatMessage from dictionary (flexible parsing)"""
        # Handle tool_calls as dicts or ToolCall objects
        tool_calls = None
        if data.get("tool_calls"):
            tool_calls = [
                tc if isinstance(tc, ToolCall) else ToolCall(**tc)
                for tc in data["tool_calls"]
            ]
        
        return cls(
            role=data["role"],
            content=data.get("content"),
            tool_calls=tool_calls,
            tool_call_id=data.get("tool_call_id"),
            name=data.get("name"),
            resource_id=data.get("resource_id"),
            timestamp=data.get("timestamp") or datetime.now(),
            sequence=data.get("sequence")
        )


class ChatHistory(BaseModel):
    """
    Manages conversation history with type safety and convenience methods.
    
    Usage:
        history = ChatHistory()
        history.add_system_message("You are a helpful assistant")
        history.add_user_message("Hello!")
        
        # Get OpenAI format for API call
        messages = history.to_openai_format()
        
        # Get new messages since a point
        new_messages = history.get_new_messages(start_index=5)
    """
    messages: List[ChatMessage] = Field(default_factory=list)
    chat_id: Optional[str] = None
    user_id: Optional[str] = None
    
    def add_message(self, message: ChatMessage) -> None:
        """Add a message to history"""
        if message.sequence is None:
            message.sequence = len(self.messages)
        self.messages.append(message)
    
    def add_system_message(self, content: str) -> None:
        """Add a system message"""
        self.add_message(ChatMessage(role="system", content=content))
    
    def add_user_message(self, content: str, images: List[Dict[str, str]] = None) -> None:
        """Add a user message with optional image attachments for multimodal"""
        image_contents = None
        if images:
            image_contents = [ImageContent(data=img["data"], media_type=img.get("media_type", "image/png")) for img in images]
        self.add_message(ChatMessage(role="user", content=content, images=image_contents))
    
    def add_assistant_message(
        self,
        content: Optional[str] = None,
        tool_calls: Optional[List[ToolCall]] = None
    ) -> None:
        """Add an assistant message (with optional tool calls)"""
        self.add_message(ChatMessage(
            role="assistant",
            content=content,
            tool_calls=tool_calls
        ))
    
    def add_tool_message(
        self,
        content: str,
        tool_call_id: str,
        name: str,
        resource_id: Optional[str] = None
    ) -> None:
        """Add a tool result message"""
        self.add_message(ChatMessage(
            role="tool",
            content=content,
            tool_call_id=tool_call_id,
            name=name,
            resource_id=resource_id
        ))
    
    def extend_from_dicts(self, messages: List[Dict[str, Any]]) -> None:
        """Add multiple messages from dictionary format"""
        for msg_dict in messages:
            self.add_message(ChatMessage.from_dict(msg_dict))
    
    def extend_from_db(self, db_messages: List) -> None:
        """Add multiple messages from database rows"""
        for db_msg in db_messages:
            self.add_message(ChatMessage.from_db(db_msg))
    
    def to_openai_format(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Convert to OpenAI API format.
        
        Args:
            limit: Optional limit on number of messages to return (most recent N messages)
        
        Returns list of dicts suitable for LLM API calls.
        """
        messages = self.messages
        if limit is not None and limit > 0:
            messages = messages[-limit:]
        return [msg.to_openai_format() for msg in messages]
    
    def to_db_format(self) -> List[Dict[str, Any]]:
        """
        Convert to database format.
        
        Returns list of dicts suitable for chat_crud operations.
        """
        return [msg.to_db_format() for msg in self.messages]
    
    def get_new_messages(self, start_index: int) -> List[ChatMessage]:
        """
        Get messages added after a certain point.
        
        Useful for getting new messages after agent processing.
        """
        return self.messages[start_index:]
    
    def get_messages_by_role(self, role: str) -> List[ChatMessage]:
        """Get all messages of a specific role"""
        return [msg for msg in self.messages if msg.role == role]
    
    def get_last_user_message(self) -> Optional[ChatMessage]:
        """Get the most recent user message"""
        user_messages = self.get_messages_by_role("user")
        return user_messages[-1] if user_messages else None
    
    def get_last_assistant_message(self) -> Optional[ChatMessage]:
        """Get the most recent assistant message"""
        assistant_messages = self.get_messages_by_role("assistant")
        return assistant_messages[-1] if assistant_messages else None
    
    def get_tool_calls_with_results(self) -> List[Dict[str, Any]]:
        """
        Get all tool calls paired with their results.
        
        Returns list of {tool_call, result_message} pairs.
        """
        tool_calls_map = {}
        tool_results = []
        
        # First pass: collect tool calls from assistant messages
        for msg in self.messages:
            if msg.role == "assistant" and msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_calls_map[tc.id] = {
                        "tool_call": tc,
                        "result": None
                    }
        
        # Second pass: match tool results
        for msg in self.messages:
            if msg.role == "tool" and msg.tool_call_id:
                if msg.tool_call_id in tool_calls_map:
                    tool_calls_map[msg.tool_call_id]["result"] = msg
                    tool_results.append(tool_calls_map[msg.tool_call_id])
        
        return tool_results
    
    def count_by_role(self) -> Dict[str, int]:
        """Get count of messages by role"""
        counts = {"system": 0, "user": 0, "assistant": 0, "tool": 0}
        for msg in self.messages:
            counts[msg.role] += 1
        return counts
    
    def __len__(self) -> int:
        """Number of messages in history"""
        return len(self.messages)
    
    def __getitem__(self, index) -> ChatMessage:
        """Access messages by index"""
        return self.messages[index]
    
    def __repr__(self) -> str:
        counts = self.count_by_role()
        return f"ChatHistory({len(self)} messages: {counts})"
    
    @classmethod
    def from_db_messages(cls, db_messages: List, chat_id: str, user_id: str) -> "ChatHistory":
        """
        Create ChatHistory from database messages.
        
        Sanitizes malformed tool calls that may have been saved during interrupted streams.
        Also removes orphaned tool responses that reference removed tool calls.
        """
        history = cls(chat_id=chat_id, user_id=user_id)
        
        # First pass: collect messages and track removed tool call IDs
        removed_tool_call_ids: Set[str] = set()
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
                "tool_calls": None
            }
            
            # Sanitize tool_calls for assistant messages
            if db_msg.role == "assistant" and db_msg.tool_calls:
                valid_tcs, removed_ids = _sanitize_tool_calls(db_msg.tool_calls)
                removed_tool_call_ids.update(removed_ids)
                msg_data["tool_calls"] = valid_tcs if valid_tcs else None
                
                if removed_ids:
                    logger.warning(f"Removed {len(removed_ids)} malformed tool calls from chat {chat_id}")
            else:
                msg_data["tool_calls"] = db_msg.tool_calls
            
            temp_messages.append(msg_data)
        
        # Second pass: filter out orphaned tool responses
        for msg_data in temp_messages:
            if msg_data["role"] == "tool":
                tool_call_id = msg_data.get("tool_call_id")
                if tool_call_id and tool_call_id in removed_tool_call_ids:
                    logger.warning(f"Removing orphaned tool response for tool call {tool_call_id}")
                    continue
            
            history.add_message(ChatMessage.from_dict(msg_data))
        
        return history
    
    @classmethod
    def from_dicts(cls, messages: List[Dict[str, Any]], chat_id: Optional[str] = None, user_id: Optional[str] = None) -> "ChatHistory":
        """
        Create ChatHistory from dictionary messages.
        
        Convenience constructor for loading from various sources.
        """
        history = cls(chat_id=chat_id, user_id=user_id)
        history.extend_from_dicts(messages)
        return history


class ChatTurn(BaseModel):
    """
    Represents a complete turn in the conversation (user message + agent response).
    
    Useful for logging and analysis.
    """
    turn_number: int
    user_message: ChatMessage
    assistant_messages: List[ChatMessage]  # May include tool calls and final response
    tool_messages: List[ChatMessage]
    timestamp: datetime = Field(default_factory=datetime.now)
    duration_ms: Optional[float] = None
    
    def to_log_format(self) -> Dict[str, Any]:
        """Convert to log format for chat logging"""
        return {
            "turn_number": self.turn_number,
            "timestamp": self.timestamp.isoformat(),
            "duration_ms": self.duration_ms,
            "user_message": self.user_message.content,
            "assistant_messages": [msg.to_openai_format() for msg in self.assistant_messages],
            "tool_calls": [
                {
                    "name": msg.name,
                    "tool_call_id": msg.tool_call_id,
                    "resource_id": msg.resource_id
                }
                for msg in self.tool_messages
            ]
        }
    
    def get_final_response(self) -> Optional[str]:
        """Get the final assistant response (last assistant message without tool calls)"""
        for msg in reversed(self.assistant_messages):
            if msg.role == "assistant" and not msg.tool_calls:
                return msg.content
        return None

