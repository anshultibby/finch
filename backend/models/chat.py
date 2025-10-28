"""
Chat-related Pydantic models (OpenAI format)
"""
from pydantic import BaseModel
from typing import Optional, Literal, List, Dict, Any


class ChatMessage(BaseModel):
    """Request model for sending a chat message"""
    message: str
    session_id: Optional[str] = None  # This is actually user_id for backward compatibility
    chat_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Response model for chat messages"""
    response: str
    session_id: str
    timestamp: str
    needs_auth: Optional[bool] = False
    tool_calls: Optional[list] = None  # List of tool call statuses


class ToolCall(BaseModel):
    """Tool call structure (OpenAI format)"""
    id: str
    type: str = "function"
    function: Dict[str, Any]  # Contains 'name' and 'arguments'


class Message(BaseModel):
    """
    Model for individual messages in chat history (OpenAI format)
    
    Roles:
    - user: User input messages
    - assistant: AI responses (may include tool_calls)
    - tool: Tool/function results (includes tool_call_id, name, and optional resource_id)
    """
    role: Literal["user", "assistant", "tool"]
    content: str
    timestamp: str
    
    # Assistant message fields
    tool_calls: Optional[List[Dict[str, Any]]] = None  # For assistant role
    latency_ms: Optional[int] = None  # For assistant role
    
    # Tool result message fields
    tool_call_id: Optional[str] = None  # For tool role
    name: Optional[str] = None  # For tool role
    resource_id: Optional[str] = None  # For tool role (FK to resources table)

