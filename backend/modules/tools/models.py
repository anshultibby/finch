"""
Models for tool system
"""
from typing import Any, Dict, Optional, Callable, Awaitable, Union, TYPE_CHECKING
from pydantic import BaseModel

if TYPE_CHECKING:
    from .stream_handler import ToolStreamHandler


class ToolContext(BaseModel):
    """
    Context passed to tools (not visible to LLM)
    Contains secure information like session_id, API keys, etc.
    """
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    stream_handler: Optional[Any] = None  # ToolStreamHandler (optional for tool streaming)
    # Add more context fields as needed
    
    class Config:
        validate_assignment = True
        arbitrary_types_allowed = True


class Tool:
    """
    A tool that can be called by the LLM.
    Wraps a Python function and provides OpenAI schema generation.
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        handler: Callable,
        parameters_schema: Dict[str, Any],
        is_async: bool,
        category: Optional[str] = None,
        requires_auth: bool = False
    ):
        self.name = name
        self.description = description
        self.handler = handler
        self.parameters_schema = parameters_schema
        self.is_async = is_async
        self.category = category
        self.requires_auth = requires_auth
    
    def to_openai_schema(self) -> Dict[str, Any]:
        """Convert to OpenAI tool calling schema"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters_schema
            }
        }

