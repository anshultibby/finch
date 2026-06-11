"""
Models for tool system
"""
import copy
from typing import Any, Dict, Optional, Callable

# Injected into every visible tool's schema so the model narrates each call.
# The value rides along in `arguments` (and thus the tool_call_start SSE event)
# and is stripped by ToolRunner before the handler is invoked.
INTENT_PARAM = "intent"
INTENT_SCHEMA = {
    "type": "string",
    "description": (
        "One short present-tense phrase (3-8 words, sentence case) telling the "
        "user what this specific call is doing, e.g. 'Comparing NVDA and AMD "
        "margins'. Shown live in the UI. Include it on every call."
    ),
}


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
        parameters = self.parameters_schema
        # Visible tools get the optional `intent` param so the model can label
        # the call for the live activity ticker. Hidden tools skip it — nobody
        # sees them, so the tokens would be wasted.
        if not self.hidden_from_ui and INTENT_PARAM not in parameters.get("properties", {}):
            parameters = copy.deepcopy(parameters)
            parameters.setdefault("properties", {})[INTENT_PARAM] = INTENT_SCHEMA
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": parameters
            }
        }

