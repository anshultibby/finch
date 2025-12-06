"""
Pydantic models for Server-Sent Events (SSE)
"""
from pydantic import BaseModel
from typing import Optional, Dict, Any, Literal, List
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
    user_description: Optional[str] = None  # User-friendly description for display
    timestamp: str = datetime.now().isoformat()


class ToolCallCompleteEvent(BaseModel):
    """Event sent when a tool call completes"""
    tool_call_id: str
    tool_name: str
    status: Literal["completed", "error"]
    resource_id: Optional[str] = None
    error: Optional[str] = None
    result_summary: Optional[str] = None  # Brief summary of result for display to user
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
    is_notification: bool = False  # True if from message_notify_user
    is_question: bool = False  # True if from message_ask_user
    suggest_takeover: Optional[str] = None  # For message_ask_user: "browser", etc.


class DoneEvent(BaseModel):
    """Event sent when streaming is complete"""
    message: str = "Stream complete"
    timestamp: str = datetime.now().isoformat()


class ErrorEvent(BaseModel):
    """Event sent when an error occurs"""
    error: str
    details: Optional[str] = None
    timestamp: str = datetime.now().isoformat()


class OptionButton(BaseModel):
    """Model for a single option button"""
    id: str  # Unique identifier for this option
    label: str  # Display text on the button
    value: str  # Value to send back when clicked
    description: Optional[str] = None  # Optional tooltip/description


class OptionsEvent(BaseModel):
    """Event sent when the assistant wants to present options to the user"""
    question: str  # The question/prompt to show above the options
    options: List[OptionButton]  # List of option buttons to display
    timestamp: str = datetime.now().isoformat()


class ToolStatusEvent(BaseModel):
    """Event sent when a tool emits a status update during execution"""
    tool_call_id: Optional[str] = None
    tool_name: Optional[str] = None
    status: str  # Status string (fetching, analyzing, processing, etc.)
    message: Optional[str] = None  # Optional detailed message
    timestamp: str = datetime.now().isoformat()


class ToolProgressEvent(BaseModel):
    """Event sent when a tool emits a progress update"""
    tool_call_id: Optional[str] = None
    tool_name: Optional[str] = None
    percent: float  # 0-100
    message: Optional[str] = None
    timestamp: str = datetime.now().isoformat()


class ToolLogEvent(BaseModel):
    """Event sent when a tool emits a log message"""
    tool_call_id: Optional[str] = None
    tool_name: Optional[str] = None
    level: Literal["debug", "info", "warning", "error"]
    message: str
    timestamp: str = datetime.now().isoformat()


# Internal agent loop events (similar to LangChain's event system)
class LLMStartEvent(BaseModel):
    """Event when LLM call starts"""
    message_count: int
    timestamp: str = datetime.now().isoformat()


class AssistantMessageDeltaEvent(BaseModel):
    """Event sent for each content delta during streaming"""
    delta: str  # The incremental content


class LLMEndEvent(BaseModel):
    """Event when LLM call completes - includes accumulated results"""
    content: str
    tool_calls: List[Dict[str, Any]]
    timestamp: str = datetime.now().isoformat()


class ToolsEndEvent(BaseModel):
    """Event when all tool executions complete - includes tool messages for conversation"""
    tool_messages: List[Dict[str, Any]]
    execution_results: Optional[List[Dict[str, Any]]] = None  # Optional: detailed results for tracking
    timestamp: str = datetime.now().isoformat()

