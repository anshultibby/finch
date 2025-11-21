"""
Agent Context - Pydantic model for agent execution context
"""
from typing import Optional, Dict, Any
from pydantic import BaseModel


class AgentContext(BaseModel):
    """
    Context for agent execution
    
    Contains all the information needed for an agent to execute:
    - User identification
    - Resource management
    - Stream handler for progress updates
    - Additional context data (e.g., brokerage connection info)
    """
    user_id: str  # Supabase user ID (OAuth identifier) - REQUIRED
    chat_id: str  # Chat session ID - REQUIRED
    resource_manager: Any  # ResourceManager instance - REQUIRED
    stream_handler: Any  # ToolStreamHandler for progress updates - REQUIRED
    data: Optional[Dict[str, Any]] = None  # Additional context data (e.g., auth status) - OPTIONAL
    
    class Config:
        validate_assignment = True
        arbitrary_types_allowed = True

