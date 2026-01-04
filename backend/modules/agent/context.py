"""
Agent Context - Pydantic model for agent execution context
"""
from typing import Optional, Dict, Any
from pydantic import BaseModel
import uuid


def generate_agent_id() -> str:
    """Generate a unique agent ID"""
    return f"agent_{uuid.uuid4().hex[:12]}"


class AgentContext(BaseModel):
    """
    Context for agent and tool execution
    
    Contains all values that need to be passed to tools but are not generated
    by the LLM and instead come from code:
    - Agent identification (for tracking which agent emitted events)
    - User identification
    - Chat session ID
    - Current tool call ID (for streaming events)
    - Parent agent ID (for nested agent tracking - e.g. delegation)
    - Additional context data (e.g., auth status, credentials)
    """
    agent_id: str  # Unique ID for this agent instance
    user_id: str  # Supabase user ID (OAuth identifier) - REQUIRED
    chat_id: str  # Chat session ID - REQUIRED
    current_tool_call_id: Optional[str] = None  # Current tool call ID for streaming events
    parent_agent_id: Optional[str] = None  # Parent agent ID (for sub-agents like executor)
    data: Optional[Dict[str, Any]] = None  # Additional context data (e.g., auth status, credentials) - OPTIONAL
    
    class Config:
        validate_assignment = True

