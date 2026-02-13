"""
Agent Context - Pydantic model for agent execution context
"""
from typing import Optional, Dict, Any
from pydantic import BaseModel
import uuid
import asyncio


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
    - Cancel event (for interrupting execution when user sends new message)
    """
    agent_id: str  # Unique ID for this agent instance
    user_id: str  # Supabase user ID (OAuth identifier) - REQUIRED
    chat_id: str  # Chat session ID - REQUIRED
    current_tool_call_id: Optional[str] = None  # Current tool call ID for streaming events
    parent_agent_id: Optional[str] = None  # Parent agent ID (for sub-agents like executor)
    data: Optional[Dict[str, Any]] = None  # Additional context data (e.g., auth status, credentials) - OPTIONAL
    cancel_event: Optional[Any] = None  # asyncio.Event for cancellation (Any to avoid Pydantic issues)
    
    class Config:
        validate_assignment = True
        arbitrary_types_allowed = True  # Allow asyncio.Event
    
    def is_cancelled(self) -> bool:
        """Check if this context has been cancelled"""
        if self.cancel_event is None:
            return False
        return self.cancel_event.is_set()
    
    def cancel(self) -> None:
        """Signal cancellation for this context"""
        if self.cancel_event is not None:
            self.cancel_event.set()


# Registry to track active agent contexts by chat_id
# When a new message comes in, we can cancel the existing context
_active_contexts: Dict[str, AgentContext] = {}


def register_context(chat_id: str, context: AgentContext) -> Optional[AgentContext]:
    """
    Register an agent context for a chat.
    Returns the previous context if one was active (caller should cancel it).
    """
    previous = _active_contexts.get(chat_id)
    _active_contexts[chat_id] = context
    return previous


def unregister_context(chat_id: str, context: AgentContext) -> None:
    """
    Unregister an agent context for a chat.
    Only removes if the context matches (prevents race conditions).
    """
    if _active_contexts.get(chat_id) is context:
        del _active_contexts[chat_id]


def get_active_context(chat_id: str) -> Optional[AgentContext]:
    """Get the currently active context for a chat"""
    return _active_contexts.get(chat_id)

