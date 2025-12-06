"""
Chat History Models - Type-safe conversation management

Provides clean abstractions for managing chat history throughout the agent loop.
"""
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    """Represents a tool call in a message"""
    id: str
    type: Literal["function"] = "function"
    function: Dict[str, Any]  # {name: str, arguments: str}


class ChatMessage(BaseModel):
    """
    Represents a single message in the conversation.
    
    Supports OpenAI message format with extensions for our use cases.
    """
    role: Literal["system", "user", "assistant", "tool"]
    content: Optional[str] = None
    
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
        
        Returns clean dict for LLM API calls.
        """
        message = {"role": self.role}
        
        if self.content is not None:
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
    
    def add_user_message(self, content: str) -> None:
        """Add a user message"""
        self.add_message(ChatMessage(role="user", content=content))
    
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
        
        Convenience constructor for loading from DB.
        """
        history = cls(chat_id=chat_id, user_id=user_id)
        history.extend_from_db(db_messages)
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

