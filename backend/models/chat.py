"""
Chat-related Pydantic models
"""
from pydantic import BaseModel
from typing import Optional, Literal


class ChatMessage(BaseModel):
    """Request model for sending a chat message"""
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Response model for chat messages"""
    response: str
    session_id: str
    timestamp: str
    needs_auth: Optional[bool] = False


class Message(BaseModel):
    """Model for individual messages in chat history"""
    role: Literal["user", "assistant"]
    content: str
    timestamp: str

