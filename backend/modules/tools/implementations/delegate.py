"""
Delegate tool — spawns a sub-agent inline with its own tool loop.

The main agent acts as a coordinator: it decomposes complex tasks into subtasks
and delegates them. Each delegate call runs a full BaseAgent loop to completion
and returns the result. Multiple delegate calls in one turn run in parallel.

Sub-agents cannot delegate further (no recursion). They write their output to
/home/user/_tasks/<task_id>.md in the sandbox for persistence and cross-reference.
"""
from typing import Dict, Any, AsyncGenerator, Union

from modules.agent.context import AgentContext, generate_agent_id
from modules.tools.decorator import tool
from schemas.sse import SSEEvent
from schemas.chat_history import ChatHistory, ChatMessage
from utils.logger import get_logger

logger = get_logger(__name__)

DELEGATE_SYSTEM_PROMPT = """You are a focused sub-agent executing a specific task delegated by a coordinator.

Your job: complete the task described below, then return a clear, structured result.

Rules:
- Execute the task completely. Don't ask clarifying questions — make reasonable assumptions.
- Write your final output to the task file path provided. This persists your work for the coordinator.
- Be thorough but concise. Include data, findings, and conclusions — not process narration.
- You have full access to the sandbox, web search, code execution, and financial data tools.
- You CANNOT delegate to other sub-agents. Do the work yourself.
- **Skills before web search.** For stock prices, fundamentals, earnings, filings, or any structured financial data, ALWAYS use skill APIs (read SKILL.md files in /home/user/skills/). Only use web search for qualitative context: news, analyst commentary, industry trends.

After completing your work, write a summary of your findings as your final message."""


@tool(
    description="Delegate a task to a sub-agent that runs to completion and returns results. Use for independent subtasks that can run in parallel. The sub-agent has access to all tools except delegate (no recursion). Write a plan to /home/user/_plan.md first to track your decomposition.",
    name="delegate",
    category="orchestration",
)
async def delegate_task(
    *,
    context: AgentContext,
    task: str,
    task_id: str,
    context_summary: str = "",
) -> AsyncGenerator[Union[SSEEvent, Dict[str, Any]], None]:
    """
    Delegate a task to a sub-agent.

    Args:
        task: Clear description of what the sub-agent should accomplish
        task_id: Short identifier for this task (used in filenames, e.g. "analyze_nvda")
        context_summary: Optional context from prior tasks or the plan that this sub-agent needs
    """
    from modules.agent.base_agent import BaseAgent
    from core.config import Config

    sub_agent_id = generate_agent_id()
    chat_dir = f"/home/user/_tasks/{context.chat_id}"
    task_file = f"{chat_dir}/{task_id}.md"

    all_tools = list(Config.AGENT_TOOLS)
    sub_tools = [t for t in all_tools if t != "delegate"]

    system_prompt = f"""{DELEGATE_SYSTEM_PROMPT}

## Your Task
{task}

## Context from Coordinator
{context_summary if context_summary else "No additional context provided."}

## Output File
Write your final output to: {task_file}
Use bash: mkdir -p {chat_dir} && cat > {task_file} << 'TASKEOF'
... your structured output ...
TASKEOF

This file will be read by the coordinator to synthesize the final answer."""

    sub_context = AgentContext(
        agent_id=sub_agent_id,
        user_id=context.user_id,
        chat_id=context.chat_id,
        parent_agent_id=context.agent_id,
        skill_ids=context.skill_ids,
        data=context.data,
        cancel_event=context.cancel_event,
    )

    agent = BaseAgent(
        context=sub_context,
        system_prompt=system_prompt,
        model=Config.AGENT_LLM_MODEL,
        tool_names=sub_tools,
        enable_tool_streaming=True,
    )

    chat_history = ChatHistory()
    chat_history.add_message(ChatMessage.from_dict({"role": "user", "content": task}))

    final_content = ""
    async for event in agent.run_tool_loop_streaming(
        initial_messages=agent.build_messages(chat_history=chat_history),
        chat_history=chat_history,
    ):
        if event.event == "message_end":
            content = event.data.get("content", "")
            if content:
                final_content = content

        if event.event in ("tool_call_start", "tool_call_complete", "tool_status", "tool_log"):
            event.data = event.data or {}
            event.data["sub_agent_id"] = sub_agent_id
            event.data["task_id"] = task_id
            yield event

    summary = final_content or "(sub-agent produced no text output)"
    if len(summary) > 3000:
        summary = summary[:3000] + "\n\n... [truncated — full output in task file]"

    yield {
        "success": True,
        "data": {
            "task_id": task_id,
            "task_file": task_file,
            "summary": summary,
        },
        "message": f"Task '{task_id}' complete. Output written to {task_file}. Summary:\n\n{summary}",
    }
