"""
Financial Code Generation Planner (Manus-inspired)

Simple task planning for Python code generation in financial context.
No "strategy" abstraction - just code generation tasks.
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class StepStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class PlanStep(BaseModel):
    number: int
    description: str
    status: StepStatus = StepStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 2


class CodeGenPlan(BaseModel):
    """Plan for generating financial analysis code"""
    task_description: str
    steps: List[PlanStep]
    current_step: int = 0
    metadata: Dict[str, Any] = {}


def create_code_plan(description: str, metadata: Dict[str, Any] = None) -> CodeGenPlan:
    """
    Create a plan for generating financial code
    
    Steps:
    1. Analyze requirements → what data/calculations needed
    2. Generate code → LLM creates Python function
    3. Validate → AST, imports, security checks
    4. Test → run with sample data
    5. Save → store for reuse
    """
    steps = [
        PlanStep(number=1, description="Analyze requirements and identify data needs"),
        PlanStep(number=2, description="Generate Python code", max_retries=3),
        PlanStep(number=3, description="Validate code (syntax, security)"),
        PlanStep(number=4, description="Test with sample data", max_retries=2),
        PlanStep(number=5, description="Save code to file"),
    ]
    
    return CodeGenPlan(
        task_description=description,
        steps=steps,
        metadata=metadata or {}
    )


def get_current_step(plan: CodeGenPlan) -> Optional[PlanStep]:
    """Get current step"""
    if plan.current_step >= len(plan.steps):
        return None
    return plan.steps[plan.current_step]


def mark_step_complete(plan: CodeGenPlan, result: Dict[str, Any] = None) -> bool:
    """Mark step complete, return True if more steps remain"""
    step = get_current_step(plan)
    if step:
        step.status = StepStatus.COMPLETED
        step.result = result
        logger.info(f"✓ Step {step.number}/{len(plan.steps)}: {step.description}")
    
    plan.current_step += 1
    return plan.current_step < len(plan.steps)


def mark_step_failed(plan: CodeGenPlan, error: str) -> Dict[str, Any]:
    """
    Mark step failed, return retry info
    
    Returns:
        {"should_retry": bool, "retry_count": int, "plan_failed": bool}
    """
    step = get_current_step(plan)
    if not step:
        return {"should_retry": False, "plan_failed": True}
    
    step.error = error
    step.retry_count += 1
    
    can_retry = step.retry_count < step.max_retries
    
    if can_retry:
        logger.warning(f"Step {step.number} failed (attempt {step.retry_count}/{step.max_retries}), retrying...")
        return {"should_retry": True, "retry_count": step.retry_count, "plan_failed": False}
    else:
        step.status = StepStatus.FAILED
        logger.error(f"✗ Step {step.number} failed permanently: {error}")
        return {"should_retry": False, "retry_count": step.retry_count, "plan_failed": True}

