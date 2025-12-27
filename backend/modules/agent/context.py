"""
Agent Context - Pydantic model for agent execution context
"""
from typing import Optional, Dict, Any
from pydantic import BaseModel


class AgentContext(BaseModel):
    """
    Context for agent and tool execution
    
    Contains all values that need to be passed to tools but are not generated
    by the LLM and instead come from code:
    - User identification
    - Chat session ID
    - Current tool call ID (for streaming events)
    - Additional context data (e.g., auth status, credentials)
    """
    user_id: str  # Supabase user ID (OAuth identifier) - REQUIRED
    chat_id: str  # Chat session ID - REQUIRED
    current_tool_call_id: Optional[str] = None  # Current tool call ID for streaming events
    data: Optional[Dict[str, Any]] = None  # Additional context data (e.g., auth status, credentials) - OPTIONAL
    
    class Config:
        validate_assignment = True

