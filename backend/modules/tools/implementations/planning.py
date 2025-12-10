"""
Planning tool implementations - Plan creation and management
"""
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from modules.agent.context import AgentContext


class PlanPhase(BaseModel):
    """A single phase in a multi-phase plan"""
    id: int = Field(..., description="Sequential phase number (1, 2, 3, ...)")
    title: str = Field(..., description="Clear, action-oriented title for this phase (becomes a heading in UI)")


def create_plan_impl(
    context: AgentContext,
    goal: str,
    phases: List[dict]
) -> Dict[str, Any]:
    """
    Create a structured plan for complex tasks.
    
    Creates a plan that groups all subsequent tool calls under phases.
    The UI will display tool calls nested under the current phase heading.
    
    Args:
        context: Agent context
        goal: Clear statement of what you're trying to accomplish
        phases: List of phases to execute sequentially. Each phase should have 'id' and 'title' fields.
    """
    # Convert dicts to PlanPhase objects
    parsed_phases = []
    for p in phases:
        if isinstance(p, dict):
            # Convert dict to PlanPhase
            parsed_phases.append(PlanPhase(**p))
        elif isinstance(p, PlanPhase):
            # Already a PlanPhase object
            parsed_phases.append(p)
        else:
            raise ValueError(f"Invalid phase type: {type(p)}")
    
    # Store the plan in context for tracking
    plan_data = {
        "goal": goal,
        "phases": [{"id": p.id, "title": p.title} for p in parsed_phases],
        "current_phase_id": 1,  # Always start at phase 1
        "created_at": "now"
    }
    
    # Return success - the plan structure is communicated to the UI via the tool call itself
    return {
        "success": True,
        "message": f"Plan created with {len(parsed_phases)} phases",
        "plan": plan_data
    }


def advance_plan_impl(context: AgentContext) -> Dict[str, Any]:
    """
    Advance to the next phase in the plan.
    
    This signals to the UI to move to the next phase section.
    """
    return {
        "success": True,
        "message": "Advanced to next phase",
        "action": "advance_phase"
    }

