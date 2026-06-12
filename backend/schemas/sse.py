"""
Pydantic models for Server-Sent Events (SSE)
"""
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
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


class ScrapedContent(BaseModel):
    """Scraped webpage content"""
    url: str
    title: str
    content: str  # Clean markdown content
    is_complete: bool = False


class FileContent(BaseModel):
    """File content for read_chat_file results"""
    filename: str
    content: str
    file_type: str = "text"
    is_complete: bool = True


class ThinkingEvent(BaseModel):
    """Event sent when AI is processing/generating response after tool calls"""
    message: str = "Generating response..."
    timestamp: str = datetime.now().isoformat()


class ThinkingDeltaEvent(BaseModel):
    """Incremental reasoning/extended-thinking tokens, streamed live to the UI.

    Distinct from the visible answer (AssistantMessageDeltaEvent) — these are
    the model's working notes, rendered as ephemeral 'thought' entries.
    """
    delta: str


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


# Internal agent loop events
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


class ToolCallDetectedEvent(BaseModel):
    """Event sent as soon as a tool call name is detected during LLM streaming.

    Fires before arguments are complete — lets the UI immediately show that
    a tool is being invoked so the user knows the model isn't stuck.
    """
    tool_call_id: str  # May be empty string if ID hasn't arrived yet
    tool_name: str
    index: int  # Position in the tool_calls array
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


class TimeEstimateEvent(BaseModel):
    """Event sent when the agent estimates how long the task will take"""
    estimated_seconds: int
    estimated_tools: int
    description: str  # Brief description of what the agent plans to do
    timestamp: str = datetime.now().isoformat()


class CancelledEvent(BaseModel):
    """Event sent when execution is cancelled due to user interruption"""
    reason: str = "User sent a new message"
    timestamp: str = datetime.now().isoformat()
