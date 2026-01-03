"""
Delegation Tool - Master Agent delegates execution to Executor Agent

Master provides direction via param, tool loads tasks.md for full context.
Executor works through tasks and calls finish_execution when done.
"""
from typing import AsyncGenerator, Dict, Any, Optional, List
from pydantic import BaseModel, Field
from models.sse import SSEEvent
from modules.agent.context import AgentContext
from modules.agent.prompts import TASK_FILE
from modules.agent import agent_config
from utils.logger import get_logger

logger = get_logger(__name__)

# Global to capture finish_execution result from Executor
_executor_finish_result: Optional[Dict[str, Any]] = None


class DelegateExecutionParams(BaseModel):
    """Parameters for delegation"""
    direction: str = Field(
        ...,
        description="What you want the Executor to focus on. E.g. 'Complete the data fetching tasks' or 'Fix the chart generation error'"
    )


class FinishExecutionParams(BaseModel):
    """Parameters for finishing execution"""
    summary: str = Field(
        ...,
        description="Summary of what was completed"
    )
    files_created: List[str] = Field(
        default_factory=list,
        description="List of files created or modified"
    )
    success: bool = Field(
        default=True,
        description="Whether execution was successful"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if execution failed"
    )


def finish_execution_impl(
    params: FinishExecutionParams,
    context: AgentContext
) -> Dict[str, Any]:
    """
    Signal that Executor is done and pass results back to Master.
    
    This sets a global that delegate_execution reads after Executor finishes.
    """
    global _executor_finish_result
    
    _executor_finish_result = {
        "summary": params.summary,
        "files_created": params.files_created,
        "success": params.success,
        "error": params.error,
    }
    
    logger.info(f"🏁 Executor finished: {params.summary[:100]}")
    
    # Return acknowledgment to Executor
    return {
        "status": "finished",
        "message": "Execution complete. Returning control to Master Agent."
    }


async def delegate_execution_impl(
    params: DelegateExecutionParams,
    context: AgentContext
) -> AsyncGenerator[SSEEvent | Dict[str, Any], None]:
    """
    Delegate execution to the Executor Agent.
    
    Combines the direction param with tasks.md content for full context.
    Executor calls finish_execution when done to pass results back.
    """
    global _executor_finish_result
    
    from modules.resource_manager import resource_manager
    from models.chat_history import ChatHistory
    
    # Reset finish result
    _executor_finish_result = None
    
    # Load tasks.md for context
    tasks_content = resource_manager.read_chat_file(
        context.user_id,
        context.chat_id,
        TASK_FILE
    )
    
    if not tasks_content:
        yield {
            "success": False,
            "error": f"No {TASK_FILE} found. Create it first with the task checklist."
        }
        return
    
    logger.info(f"🔄 Delegating: {params.direction}")
    
    yield SSEEvent(
        event="tool_status",
        data={"status": "delegating", "message": f"Executor: {params.direction[:50]}..."}
    )
    
    executor = agent_config.create_executor_agent(context)
    
    # Create minimal history
    history = ChatHistory(chat_id=context.chat_id, user_id=context.user_id)
    user_message = f"""{params.direction}

Here is the current task file (`{TASK_FILE}`):

```markdown
{tasks_content}
```
"""
    history.add_user_message(user_message)
    
    # Run executor and stream events
    async for event in executor.process_message_stream(
        message=user_message,
        chat_history=history,
        history_limit=10
    ):
        yield event
    
    # Check if Executor called finish_execution
    if _executor_finish_result:
        result = _executor_finish_result
        yield {
            "success": result["success"],
            "error": result.get("error"),
            "summary": result["summary"],
            "files_created": result["files_created"],
            "message": result["summary"]
        }
    else:
        # Executor didn't call finish_execution - return generic result
        yield {
            "success": True,
            "summary": "Executor completed without explicit finish signal",
            "files_created": [],
            "message": "Execution completed"
        }
    
    logger.info(f"✅ Executor finished")
