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
        # Use string concatenation to avoid f-string interpreting JSON curly braces as format specs
        return "event: " + self.event + "\ndata: " + json.dumps(self.data) + "\n\n"


class ToolCallStartEvent(BaseModel):
    """Event sent when a tool call starts"""
    tool_call_id: str
    tool_name: str
    arguments: Dict[str, Any]
    user_description: Optional[str] = None  # User-friendly description for display
    timestamp: str = datetime.now().isoformat()


class CodeOutput(BaseModel):
    """Code execution output"""
    stdout: Optional[str] = None
    stderr: Optional[str] = None


class SearchResult(BaseModel):
    """A single search result"""
    title: str
    link: str
    snippet: str
    date: Optional[str] = None  # For news results
    source: Optional[str] = None  # For news results (publication name)
    imageUrl: Optional[str] = None  # Thumbnail/favicon
    position: Optional[int] = None  # Result rank


class SearchAnswerBox(BaseModel):
    """Featured snippet / answer box from search"""
    title: Optional[str] = None
    answer: Optional[str] = None
    snippet: Optional[str] = None


class SearchKnowledgeGraph(BaseModel):
    """Knowledge panel from search"""
    title: Optional[str] = None
    type: Optional[str] = None
    description: Optional[str] = None
    imageUrl: Optional[str] = None


class SearchResults(BaseModel):
    """Web/news search results"""
    query: str
    results: List[SearchResult]
    answerBox: Optional[SearchAnswerBox] = None
    knowledgeGraph: Optional[SearchKnowledgeGraph] = None
    is_complete: bool = False


class ToolCallCompleteEvent(BaseModel):
    """Event sent when a tool call completes"""
    tool_call_id: str
    tool_name: str
    status: Literal["completed", "error"]
    resource_id: Optional[str] = None
    error: Optional[str] = None
    result_summary: Optional[str] = None  # Brief summary of result for display to user
    code_output: Optional[CodeOutput] = None  # Code execution output (stdout/stderr)
    search_results: Optional[SearchResults] = None  # Web/news search results
    timestamp: str = datetime.now().isoformat()


class ThinkingEvent(BaseModel):
    """Event sent when AI is processing/generating response after tool calls"""
    message: str = "Generating response..."
    timestamp: str = datetime.now().isoformat()


class MessageEndEvent(BaseModel):
    """Event sent when assistant message is complete (with or without tool calls)"""
    role: str = "assistant"
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    timestamp: str = datetime.now().isoformat()


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


class FileContentEvent(BaseModel):
    """Event sent when file content is being written (for streaming file writes)"""
    tool_call_id: str
    filename: str
    content: str  # The file content (can be sent in chunks or all at once)
    file_type: str = "text"  # python, json, csv, markdown, etc.
    is_complete: bool = False  # True when file write is complete
    timestamp: str = datetime.now().isoformat()


class ToolCallStreamingEvent(BaseModel):
    """Event sent during LLM streaming when tool call arguments are being generated.
    
    This is used to stream file content BEFORE tool execution starts,
    allowing the UI to show file content as the LLM generates it.
    """
    tool_call_id: str
    tool_name: str
    arguments_delta: str  # The incremental JSON argument string
    # For file tools, we extract and send these directly for easier frontend handling
    filename: Optional[str] = None
    file_content_delta: Optional[str] = None  # Incremental file content
    timestamp: str = datetime.now().isoformat()


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
