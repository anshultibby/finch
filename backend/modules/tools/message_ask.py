"""
Message ask tool - Blocking questions that require user response

Like Manus's message_ask_user tool.
"""
from typing import Optional, List, Union, AsyncGenerator, Literal
from modules.tools import tool
from modules.agent.context import AgentContext
from models.sse import SSEEvent
from utils.logger import get_logger

logger = get_logger(__name__)


@tool(
    description="Ask user a question and wait for response. Use for requesting clarification, asking for confirmation, or gathering additional information.",
    name="message_ask_user",
    category="communication"
)
async def message_ask_user(
    *,
    text: str,
    attachments: Optional[Union[str, List[str]]] = None,
    suggest_user_takeover: Literal["none", "browser"] = "none",
    context: AgentContext
) -> AsyncGenerator[SSEEvent, None]:
    """
    Ask the user a question and wait for their response.
    
    This tool pauses agent execution until the user provides an answer.
    Use for clarifications, confirmations, or gathering additional information.
    
    Args:
        text: Question text to present
        attachments: Optional file paths or URLs to attach
        suggest_user_takeover: Whether to suggest user takeover (browser, etc.)
        context: Agent execution context
        
    Yields:
        SSEEvent for the question and eventual response
    """
    logger.info(f"❓ Asking user: {text[:100]}...")
    
    # Normalize attachments to list
    attachment_list = []
    if attachments:
        if isinstance(attachments, str):
            attachment_list = [attachments]
        else:
            attachment_list = list(attachments)
    
    # Format attachments as [file:name] if they're file paths
    formatted_text = text
    if attachment_list:
        attachment_refs = []
        for att in attachment_list:
            # If it looks like a file path (not a URL), format as [file:name]
            if not att.startswith(('http://', 'https://')):
                # Extract just the filename
                filename = att.split('/')[-1]
                attachment_refs.append(f"[file:{filename}]")
            else:
                attachment_refs.append(att)
        
        if attachment_refs:
            formatted_text = f"{text}\n\n" + " ".join(attachment_refs)
    
    # Emit question event - this will pause the agent loop
    # The frontend should display this and wait for user input
    # When user responds, it becomes a new user message in the conversation
    yield SSEEvent(
        event="assistant_message",
        data={
            "content": formatted_text,
            "is_question": True,
            "suggest_takeover": suggest_user_takeover
        }
    )
    
    # Return a result that tells the LLM to wait
    # The agent loop should STOP here and wait for the next user message
    result = "⏸️  Waiting for user response. Agent will resume when user replies."
    
    yield SSEEvent(
        event="tool_result",
        data={
            "result": result,
            "requires_user_input": True  # Signal to agent loop to stop
        }
    )

