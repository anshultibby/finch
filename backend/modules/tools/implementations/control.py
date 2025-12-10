"""
Control tool implementations - System control signals
"""
from typing import Dict, Any
from modules.agent.context import AgentContext


def idle_impl(context: AgentContext) -> Dict[str, Any]:
    """Signal completion and return to idle state"""
    return {
        "success": True,
        "message": "Ready for next input",
        "state": "idle"
    }

