"""
Pydantic models for resources
"""
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime


class ResourceMetadata(BaseModel):
    """Metadata about how a resource was created"""
    parameters: Optional[Dict[str, Any]] = None
    tool_call_id: Optional[str] = None
    execution_time_ms: Optional[int] = None


class ResourceResponse(BaseModel):
    """Response model for a resource"""
    id: str
    chat_id: str
    user_id: str
    tool_name: str
    resource_type: str
    title: str
    data: Dict[str, Any]
    metadata: Optional[ResourceMetadata] = None
    created_at: str


class ToolCallStatus(BaseModel):
    """Status of a tool call (for ephemeral UI messages)"""
    tool_call_id: str
    tool_name: str
    status: str  # 'calling', 'completed', 'error'
    resource_id: Optional[str] = None
    error: Optional[str] = None


class ToolCallInfo(BaseModel):
    """Information about tool calls made during a response"""
    tool_calls: List[ToolCallStatus]
    has_tool_calls: bool

