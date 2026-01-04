"""
Delegation Tool - Master Agent delegates execution to Executor Agent

Master provides direction via param, tool loads tasks.md for full context.
Executor works through tasks and calls finish_execution when done.
"""
from typing import AsyncGenerator, Dict, Any, Optional, List
from pydantic import BaseModel, Field
from models.sse import SSEEvent
from modules.agent.context import AgentContext, generate_agent_id
from modules.agent.prompts import TASK_FILE
from modules.agent import agent_config
from utils.logger import get_logger

logger = get_logger(__name__)


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
    
    Returns a result that delegate_execution_impl detects in the event stream.
    """
    logger.info(f"🏁 Executor finished: {params.summary[:100]}")
    
    # Return the finish signal - delegate_execution_impl will detect this
    return {
        "status": "finished",
        "summary": params.summary,
        "files_created": params.files_created,
        "success": params.success,
        "error": params.error,
    }


def _extract_finish_result_from_event(event: SSEEvent) -> Optional[Dict[str, Any]]:
    """
    Check if a tools_end event contains a finish_execution result.
    
    Uses execution_results which contains structured result_data,
    avoiding fragile JSON parsing of content blocks.
    
    Returns the finish result if found, None otherwise.
    """
    if not isinstance(event, SSEEvent) or event.event != "tools_end":
        return None
    
    # Use execution_results for cleaner access to tool results
    execution_results = event.data.get("execution_results", [])
    for result in execution_results:
        if result.get("tool_name") == "finish_execution":
            result_data = result.get("result_data", {})
            if isinstance(result_data, dict) and result_data.get("status") == "finished":
                return result_data
    
    return None


async def delegate_execution_impl(
    params: DelegateExecutionParams,
    context: AgentContext
) -> AsyncGenerator[SSEEvent | Dict[str, Any], None]:
    """
    Delegate execution to the Executor Agent.
    
    Combines the direction param with tasks.md content for full context.
    Executor calls finish_execution when done to pass results back.
    """
    from modules.resource_manager import resource_manager
    from models.chat_history import ChatHistory
    
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
    
    # Create a new agent ID for the executor
    executor_agent_id = generate_agent_id()
    
    # Signal delegation start to frontend with agent IDs
    yield SSEEvent(
        event="delegation_start",
        data={
            "direction": params.direction,
            "agent_id": executor_agent_id,
            "parent_agent_id": context.agent_id
        }
    )
    
    # Create a new context for the executor with its own agent_id
    # parent_agent_id links back to the master agent
    executor_context = AgentContext(
        agent_id=executor_agent_id,
        user_id=context.user_id,
        chat_id=context.chat_id,
        parent_agent_id=context.agent_id,  # Link to parent (master) agent
        data=context.data
    )
    
    executor = agent_config.create_executor_agent(executor_context)
    
    # Create minimal history
    history = ChatHistory(chat_id=context.chat_id, user_id=context.user_id)
    user_message = f"""{params.direction}

Here is the current task file (`{TASK_FILE}`):

```markdown
{tasks_content}
```
"""
    history.add_user_message(user_message)
    
    finish_result = None
    async for event in executor.process_message_stream(
        message=user_message,
        chat_history=history,
        history_limit=10
    ):
        yield event
        
        # Capture finish_execution result when it appears
        result = _extract_finish_result_from_event(event)
        if result:
            finish_result = result
    
    # Build the final result
    if finish_result:
        final_result = {
            "success": finish_result.get("success", True),
            "error": finish_result.get("error"),
            "summary": finish_result.get("summary", "Execution completed"),
            "files_created": finish_result.get("files_created", []),
            "message": finish_result.get("summary", "Execution completed")
        }
    else:
        final_result = {
            "success": True,
            "summary": "Executor completed without explicit finish signal",
            "files_created": [],
            "message": "Execution completed"
        }
    
    # Signal delegation end to frontend
    yield SSEEvent(
        event="delegation_end",
        data=final_result
    )
    
    logger.info(f"✅ Executor finished, yielding final result: {final_result}")
    
    # Yield the result dict for the tool response
    # This is what the tool executor uses to build tool_call_complete
    yield final_result
