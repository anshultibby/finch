"""
Models for tool system
"""
from typing import Any, Dict, Optional, Callable

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
        requires_auth: bool = False,
        hidden_from_ui: bool = False,
        api_docs_only: bool = False
    ):
        self.name = name
        self.description = description
        self.handler = handler
        self.parameters_schema = parameters_schema
        self.is_async = is_async
        self.category = category
        self.requires_auth = requires_auth
        self.hidden_from_ui = hidden_from_ui
        self.api_docs_only = api_docs_only
    
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

