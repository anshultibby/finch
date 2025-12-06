"""
Message notification tool - Non-blocking progress updates to user

Like Manus's message_notify_user tool.
"""
from typing import Optional, List, Union, AsyncGenerator
from modules.tools import tool
from modules.agent.context import AgentContext
from models.sse import SSEEvent
from utils.logger import get_logger

logger = get_logger(__name__)


@tool(
    description="Send a message to user without requiring a response. Use for acknowledging receipt of messages, providing progress updates, reporting task completion, or explaining changes in approach.",
    name="message_notify_user",
    category="communication"
)
async def message_notify_user(
    *,
    text: str,
    attachments: Optional[Union[str, List[str]]] = None,
    context: AgentContext
) -> AsyncGenerator[SSEEvent, None]:
    """
    Send a non-blocking notification message to the user.
    
    This tool allows the agent to provide progress updates, confirmations,
    and explanations without requiring a response from the user.
    
    Args:
        text: Message text to display
        attachments: Optional file paths or URLs to attach (supports [file:name] syntax)
        context: Agent execution context
        
    Yields:
        SSEEvent for the notification
    """
    logger.info(f"📢 Notifying user: {text[:100]}...")
    
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
    
    # Emit notification event
    # This will be caught by the frontend and displayed as an assistant message
    yield SSEEvent(
        event="assistant_message",
        data={
            "content": formatted_text,
            "is_notification": True
        }
    )
    
    # Return success message (this becomes the tool result)
    result = f"Message sent to user: {text[:80]}{'...' if len(text) > 80 else ''}"
    
    yield SSEEvent(
        event="tool_result",
        data={
            "result": result
        }
    )

