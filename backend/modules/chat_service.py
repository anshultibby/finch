"""
Chat service for managing chat sessions and interactions
"""
from typing import List, AsyncGenerator, Dict, Any
import json
import asyncio
from .agent.prompts import get_finch_system_prompt
from .agent.agent_config import create_main_agent
from config import Config
from .context_manager import context_manager
from database import AsyncSessionLocal
from modules.agent.context import AgentContext
from models.chat_history import ChatHistory
from crud import chat_async
from utils.logger import get_logger
from utils.tracing import get_tracer
from modules.tools import tool_registry

logger = get_logger(__name__)
tracer = get_tracer(__name__)


class ChatService:
    """Service for handling chat operations"""
    
    def __init__(self):
        # Don't create a shared agent instance - create one per request
        # to avoid state conflicts with concurrent requests
        pass
    
    async def send_message_stream(
        self,
        message: str,
        chat_id: str,
        user_id: str,
        images: List[Dict[str, str]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Send a message and stream SSE events as they happen.
        
        Messages are saved INCREMENTALLY as they complete during streaming.
        This ensures that if the stream is interrupted (user sends new message),
        completed work is preserved in the database.
        
        Args:
            message: User message content
            chat_id: Chat identifier
            user_id: User identifier (for SnapTrade tools)
            images: Optional list of image attachments [{"data": base64, "media_type": "image/png"}]
            
        Yields:
            SSE formatted strings (event: <type>\\ndata: <json>\\n\\n)
        """
        # OpenTelemetry will automatically trace database and HTTP calls
        # We just add high-level spans for business logic
        with tracer.start_as_current_span("chat_turn"):
            logger.info(f"Starting chat turn for user {user_id}")
            
            # STEP 1: Load history and save user message
            async with AsyncSessionLocal() as db:
                db_chat = await chat_async.get_chat(db, chat_id)
                if not db_chat:
                    await chat_async.create_chat(db, chat_id, user_id)
                
                # Load chat history using ChatHistory model
                db_messages = await chat_async.get_chat_messages(db, chat_id)
                history = ChatHistory.from_db_messages(db_messages, chat_id, user_id)
                
                # Save user message FIRST before streaming
                current_sequence = await chat_async.get_next_sequence(db, chat_id)
                await chat_async.create_message(
                    db=db,
                    chat_id=chat_id,
                    role="user",
                    content=message,
                    sequence=current_sequence
                )
                current_sequence += 1
            
            # STEP 2: Process message and save incrementally
            context = context_manager.get_all_context(user_id)
            
            agent_context = AgentContext(
                user_id=user_id,
                chat_id=chat_id,
                data=context
            )
            
            agent = create_main_agent(
                context=agent_context,
                system_prompt=get_finch_system_prompt(),
                model=Config.LLM_MODEL
            )
            
            # Add user message to history (with optional images for multimodal)
            history.add_user_message(message, images=images)
            
            # Track pending assistant message (with tool calls) for saving after tools complete
            pending_assistant_msg = None
            
            # Stream events from agent and save completed messages incrementally
            with tracer.start_as_current_span("agent_processing"):
                async for event in agent.process_message_stream(
                    message=message,
                    chat_history=history,
                    history_limit=Config.CHAT_HISTORY_LIMIT
                ):
                    # Log event type for debugging
                    if event.event == "tool_call_start":
                        logger.info(f"🚀 Yielding tool_call_start event to client: {event.data}")
                    
                    # INCREMENTAL SAVE: Save completed messages as they happen
                    # This ensures interrupted streams don't lose completed work
                    
                    if event.event == "message_end":
                        # message_end signals a complete assistant message
                        tool_calls = event.data.get("tool_calls")
                        content = event.data.get("content", "")
                        
                        if tool_calls:
                            # Assistant message with tool calls - save after tools complete
                            logger.info(f"📝 message_end with {len(tool_calls)} tool calls - setting pending_assistant_msg")
                            pending_assistant_msg = {
                                "content": content,
                                "tool_calls": tool_calls
                            }
                        else:
                            # Final assistant message (no tool calls) - save synchronously
                            seq = current_sequence
                            current_sequence += 1
                            
                            async with AsyncSessionLocal() as db:
                                await chat_async.create_message(
                                    db=db,
                                    chat_id=chat_id,
                                    role="assistant",
                                    content=content,
                                    sequence=seq
                                )
                                logger.info(f"💾 Saved final assistant message (seq={seq})")
                    
                    elif event.event == "tools_end":
                        # tools_end signals tool execution is complete
                        # Now save: 1) assistant message with tool_calls, 2) tool result messages
                        tool_messages = event.data.get("tool_messages", [])
                        
                        logger.info(f"🔧 tools_end event - pending_assistant_msg={'SET' if pending_assistant_msg else 'NONE'}, {len(tool_messages)} tool messages")
                        
                        # Save synchronously to ensure proper message ordering
                        async with AsyncSessionLocal() as db:
                            seq = current_sequence
                            # Save assistant message with tool calls
                            if pending_assistant_msg:
                                await chat_async.create_message(
                                    db=db,
                                    chat_id=chat_id,
                                    role="assistant",
                                    content=pending_assistant_msg["content"],
                                    sequence=seq,
                                    tool_calls=pending_assistant_msg["tool_calls"]
                                )
                                logger.info(f"💾 Saved assistant message with {len(pending_assistant_msg['tool_calls'])} tool calls (seq={seq})")
                                seq += 1
                                current_sequence += 1
                            
                            # Save tool result messages
                            for tool_msg in tool_messages:
                                # Handle multimodal content (list) by serializing to JSON
                                content = tool_msg.get("content", "")
                                if isinstance(content, list):
                                    content = json.dumps(content)
                                
                                await chat_async.create_message(
                                    db=db,
                                    chat_id=chat_id,
                                    role="tool",
                                    content=content,
                                    sequence=seq,
                                    tool_call_id=tool_msg.get("tool_call_id"),
                                    name=tool_msg.get("name")
                                )
                                seq += 1
                                current_sequence += 1
                            
                            if tool_messages:
                                logger.info(f"💾 Saved {len(tool_messages)} tool result messages")
                        
                        pending_assistant_msg = None
                    
                    # Yield the SSE formatted event to client
                    yield event.to_sse_format()
            
            logger.info("Chat turn complete - all messages saved incrementally")
    
    async def get_chat_history(self, chat_id: str) -> List[dict]:
        """Get chat history for a chat, including tool calls (OpenAI format)"""
        async with AsyncSessionLocal() as db:
            messages = await chat_async.get_chat_messages(db, chat_id)
            history = ChatHistory.from_db_messages(messages, chat_id, user_id=None)
            return history.to_openai_format()
    
    async def clear_chat(self, chat_id: str) -> bool:
        """Clear chat history for a chat"""
        async with AsyncSessionLocal() as db:
            count = await chat_async.clear_chat_messages(db, chat_id)
            return count > 0
    
    async def chat_exists(self, chat_id: str) -> bool:
        """Check if chat exists"""
        async with AsyncSessionLocal() as db:
            return await chat_async.get_chat(db, chat_id) is not None
    
    async def get_user_chats(self, user_id: str, limit: int = 50) -> List[dict]:
        """Get all chats for a user with last message preview (single optimized query)"""
        async with AsyncSessionLocal() as db:
            # Use optimized function that gets chats and previews in a single query
            return await chat_async.get_user_chats_with_preview(db, user_id, limit)
    
    async def get_chat_history_for_display(self, chat_id: str) -> Dict[str, Any]:
        """
        Get chat history formatted for UI display.
        
        SIMPLE: Each message has content and optional tool_calls attached directly.
        Frontend just renders messages in order.
        """
        async with AsyncSessionLocal() as db:
            messages = await chat_async.get_chat_messages(db, chat_id)
            
            if not messages:
                return {"messages": []}
            
            display_messages = []
            
            for msg in messages:
                # User messages
                if msg.role == "user":
                    display_messages.append({
                        "role": "user",
                        "content": msg.content,
                        "timestamp": msg.timestamp.isoformat() if msg.timestamp else None
                    })
                
                # Assistant messages
                elif msg.role == "assistant":
                    # Parse tool_calls if present
                    tool_calls = []
                    if msg.tool_calls:
                        for tc in msg.tool_calls:
                            tool_name = tc.get("function", {}).get("name")
                            
                            # Skip hidden tools
                            tool_obj = tool_registry.get_tool(tool_name)
                            if tool_obj and tool_obj.hidden_from_ui:
                                continue
                            
                            # Parse arguments
                            try:
                                args_str = tc.get("function", {}).get("arguments", "{}")
                                # Handle both string and dict formats
                                if isinstance(args_str, str):
                                    args = json.loads(args_str) if args_str else {}
                                elif isinstance(args_str, dict):
                                    args = args_str
                                else:
                                    args = {}
                                
                                # Use statusMessage to match ToolCallStatus interface
                                # Fall back to tool_name if no user_description provided
                                status_message = args.get("user_description") or tool_name
                                
                                tool_calls.append({
                                    "tool_call_id": tc.get("id"),
                                    "tool_name": tool_name,
                                    "statusMessage": status_message,
                                    "arguments": args,  # Include arguments for filename extraction
                                    "status": "completed"
                                })
                            except Exception as e:
                                logger.warning(f"Failed to parse tool call {tool_name}: {e}")
                                logger.exception(e)
                    
                    # Only add message if it has content or tool_calls
                    if msg.content or tool_calls:
                        display_messages.append({
                            "role": "assistant",
                            "content": msg.content or "",
                            "timestamp": msg.timestamp.isoformat() if msg.timestamp else None,
                            "tool_calls": tool_calls if tool_calls else None
                        })
                
                # Skip tool response messages (internal)
                elif msg.role == "tool":
                    continue
            
            return {"messages": display_messages}

