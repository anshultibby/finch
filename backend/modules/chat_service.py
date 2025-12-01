"""
Chat service for managing chat sessions and interactions
"""
from typing import List, AsyncGenerator
from .agent.prompts import FINCH_SYSTEM_PROMPT
from .agent.agent_config import create_main_agent
from config import Config
from .context_manager import context_manager
from database import AsyncSessionLocal
from modules.agent.context import AgentContext
from models.chat_history import ChatHistory
from crud import chat_async
from utils.logger import get_logger
from utils.tracing import get_tracer

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
        user_id: str
    ) -> AsyncGenerator[str, None]:
        """
        Send a message and stream SSE events as they happen
        
        Args:
            message: User message content
            chat_id: Chat identifier
            user_id: User identifier (for SnapTrade tools)
            
        Yields:
            SSE formatted strings (event: <type>\\ndata: <json>\\n\\n)
        """
        # OpenTelemetry will automatically trace database and HTTP calls
        # We just add high-level spans for business logic
        with tracer.start_as_current_span("chat_turn"):
            logger.info(f"Starting chat turn for user {user_id}")
            
            async with AsyncSessionLocal() as db:
                # Database calls are auto-traced by OpenTelemetry
                db_chat = await chat_async.get_chat(db, chat_id)
                if not db_chat:
                    await chat_async.create_chat(db, chat_id, user_id)
                
                # Load chat history using ChatHistory model
                db_messages = await chat_async.get_chat_messages(db, chat_id)
                history = ChatHistory.from_db_messages(db_messages, chat_id, user_id)
                context = context_manager.get_all_context(user_id)
                
                agent_context = AgentContext(
                    user_id=user_id,
                    chat_id=chat_id,
                    data=context  # Additional context data (auth status, credentials, etc.)
                )
                
                # Create agent using centralized factory (one per request to avoid state conflicts)
                agent = create_main_agent(
                    context=agent_context,
                    system_prompt=FINCH_SYSTEM_PROMPT,
                    model=Config.LLM_MODEL
                )
                
                # Save user message FIRST before streaming
                # Get next sequence from DB to avoid conflicts
                start_sequence = await chat_async.get_next_sequence(db, chat_id)
                await chat_async.create_message(
                    db=db,
                    chat_id=chat_id,
                    role="user",
                    content=message,
                    sequence=start_sequence
                )
                
                # Add user message to history
                history.add_user_message(message)
                
                # Stream events from agent (LLM calls auto-traced by OpenTelemetry)
                with tracer.start_as_current_span("agent_processing"):
                    async for event in agent.process_message_stream(
                        message=message,
                        chat_history=history
                    ):
                        # Yield the SSE formatted event
                        yield event.to_sse_format()
                
                # After streaming, save new messages to database
                new_messages = agent.get_new_messages()
                logger.info(f"Saving {len(new_messages)} messages to database")
                
                # Save messages with proper sequencing
                sequence = start_sequence + 1
                
                for msg in new_messages:
                    content = msg.content or ""
                    
                    # Convert to DB format and save
                    await chat_async.create_message(
                        db=db,
                        chat_id=chat_id,
                        role=msg.role,
                        content=content,
                        sequence=sequence,
                        tool_calls=[tc.model_dump() for tc in msg.tool_calls] if msg.tool_calls else None,
                        tool_call_id=msg.tool_call_id,
                        name=msg.name
                    )
                    sequence += 1
                
                logger.info("Saved conversation history")
    
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
        """Get all chats for a user"""
        async with AsyncSessionLocal() as db:
            chats = await chat_async.get_user_chats(db, user_id, limit)
            return [
                {
                    "chat_id": chat.chat_id,
                    "title": chat.title,
                    "created_at": chat.created_at.isoformat(),
                    "updated_at": chat.updated_at.isoformat()
                }
                for chat in chats
            ]

