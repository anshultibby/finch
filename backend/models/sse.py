"""
Pydantic models for Server-Sent Events (SSE)
"""
from pydantic import BaseModel
from typing import Optional, Dict, Any, Literal
from datetime import datetime


class SSEEvent(BaseModel):
    """Base SSE event model"""
    event: str  # Event type
    data: Dict[str, Any]  # Event data
    
    def to_sse_format(self) -> str:
        """Convert to SSE format: event: <type>\ndata: <json>\n\n"""
        import json
        return f"event: {self.event}\ndata: {json.dumps(self.data)}\n\n"


class ToolCallStartEvent(BaseModel):
    """Event sent when a tool call starts"""
    tool_call_id: str
    tool_name: str
    arguments: Dict[str, Any]
    timestamp: str = datetime.now().isoformat()


class ToolCallCompleteEvent(BaseModel):
    """Event sent when a tool call completes"""
    tool_call_id: str
    tool_name: str
    status: Literal["completed", "error"]
    resource_id: Optional[str] = None
    error: Optional[str] = None
    timestamp: str = datetime.now().isoformat()


class ThinkingEvent(BaseModel):
    """Event sent when AI is processing/generating response after tool calls"""
    message: str = "Generating response..."
    timestamp: str = datetime.now().isoformat()


class AssistantMessageEvent(BaseModel):
    """Event sent when the assistant's final message is ready"""
    content: str
    timestamp: str
    needs_auth: bool = False


class DoneEvent(BaseModel):
    """Event sent when streaming is complete"""
    message: str = "Stream complete"
    timestamp: str = datetime.now().isoformat()


class ErrorEvent(BaseModel):
    """Event sent when an error occurs"""
    error: str
    details: Optional[str] = None
    timestamp: str = datetime.now().isoformat()

