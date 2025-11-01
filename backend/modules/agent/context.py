"""
Agent Context - Pydantic model for agent execution context
"""
from typing import Optional, Dict, Any, TYPE_CHECKING
from pydantic import BaseModel

if TYPE_CHECKING:
    from modules.resource_manager import ResourceManager


class AgentContext(BaseModel):
    """
    Context for agent execution
    
    Contains all the information needed for an agent to execute:
    - User identification
    - Resource management
    - Additional context data (e.g., brokerage connection info)
    """
    user_id: Optional[str] = None  # Supabase user ID (OAuth identifier)
    chat_id: Optional[str] = None
    resource_manager: Optional[Any] = None  # ResourceManager instance
    data: Optional[Dict[str, Any]] = None  # Additional context data (e.g., auth status)
    
    class Config:
        validate_assignment = True
        arbitrary_types_allowed = True

