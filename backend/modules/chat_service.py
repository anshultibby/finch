"""
Chat service for managing chat sessions and interactions
"""
from typing import List, AsyncGenerator
from .agent import ChatAgent
from .context_manager import context_manager
from .resource_manager import ResourceManager
from database import SessionLocal, AsyncSessionLocal
from modules.agent.context import AgentContext
from modules.tools.stream_handler import ToolStreamHandler
from models.chat_history import ChatHistory
from crud import chat as chat_crud
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
            
            # Create a new agent instance for this request to avoid
            # state conflicts with concurrent requests
            agent = ChatAgent()
            
            async with AsyncSessionLocal() as db:
                # Database calls are auto-traced by OpenTelemetry
                db_chat = await chat_async.get_chat(db, chat_id)
                if not db_chat:
                    await chat_async.create_chat(db, chat_id, user_id)
                
                # Load chat history using ChatHistory model
                db_messages = await chat_async.get_chat_messages(db, chat_id)
                history = ChatHistory.from_db_messages(db_messages, chat_id, user_id)
                context = context_manager.get_all_context(user_id)
                
                # Load resources
                resource_manager = ResourceManager(chat_id=chat_id, user_id=user_id, db=None)
                with SessionLocal() as sync_db:
                    resource_manager.load_resources(db=sync_db, limit=50)
                
                # Create placeholder stream handler (ChatAgent will replace with real one)
                placeholder_stream_handler = ToolStreamHandler()
                
                agent_context = AgentContext(
                    user_id=user_id,
                    chat_id=chat_id,
                    resource_manager=resource_manager,
                    stream_handler=placeholder_stream_handler,
                    data=context  # Additional context data (auth status, etc.)
                )
                
                # Save user message FIRST before streaming
                start_sequence = len(history)
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
                        chat_history=history,
                        agent_context=agent_context
                    ):
                        # Yield the SSE formatted event
                        yield event.to_sse_format()
                
                # After streaming, save new messages to database
                new_messages = agent.get_new_messages()
                logger.info(f"Saving {len(new_messages)} messages to database")
                
                # Get tool call information to extract resource_ids from results
                tool_calls_info = agent.get_tool_calls_info()
                
                # Extract resource_ids from tool results (tools write directly to DB now)
                tool_call_to_resource = {}
                plot_resources = []
                
                for tool_call_info in tool_calls_info:
                    if tool_call_info["status"] == "completed" and tool_call_info.get("result_data"):
                        result_data = tool_call_info["result_data"]
                        
                        # Check if tool returned a resource_id
                        if "resource_id" in result_data and result_data["resource_id"]:
                            resource_id = result_data["resource_id"]
                            tool_call_to_resource[tool_call_info["tool_call_id"]] = resource_id
                            logger.debug(f"Tool call {tool_call_info['tool_call_id']} created resource {resource_id}")
                            
                            # Track plot resources for appending to final message
                            if result_data.get("resource_type") == "plot":
                                plot_resources.append(result_data.get("title", "Chart"))
                
                # Save messages with proper sequencing
                sequence = start_sequence + 1
                
                for msg in new_messages:
                    content = msg.content or ""
                    
                    # Append plot references to final assistant message
                    if msg.role == "assistant" and content and plot_resources and msg == new_messages[-1]:
                        # This is the final assistant message, append plot markers
                        for plot_title in plot_resources:
                            content += f"\n\n[plot:{plot_title}]"
                    
                    # Link tool result messages to resources
                    resource_id = msg.resource_id
                    if msg.role == "tool" and msg.tool_call_id and not resource_id:
                        resource_id = tool_call_to_resource.get(msg.tool_call_id)
                    
                    # Convert to DB format and save
                    await chat_async.create_message(
                        db=db,
                        chat_id=chat_id,
                        role=msg.role,
                        content=content,
                        sequence=sequence,
                        resource_id=resource_id,
                        tool_calls=[tc.model_dump() for tc in msg.tool_calls] if msg.tool_calls else None,
                        tool_call_id=msg.tool_call_id,
                        name=msg.name
                    )
                    sequence += 1
                
                logger.info("Saved conversation history")
    
    def get_chat_history(self, chat_id: str) -> List[dict]:
        """Get chat history for a chat, including tool calls (OpenAI format)"""
        db = SessionLocal()
        try:
            messages = chat_crud.get_chat_messages(db, chat_id)
            history = ChatHistory.from_db_messages(messages, chat_id, user_id=None)
            return history.to_openai_format()
        finally:
            db.close()
    
    def clear_chat(self, chat_id: str) -> bool:
        """Clear chat history for a chat"""
        db = SessionLocal()
        try:
            count = chat_crud.clear_chat_messages(db, chat_id)
            return count > 0
        finally:
            db.close()
    
    def chat_exists(self, chat_id: str) -> bool:
        """Check if chat exists"""
        db = SessionLocal()
        try:
            return chat_crud.get_chat(db, chat_id) is not None
        finally:
            db.close()
    
    def get_user_chats(self, user_id: str, limit: int = 50) -> List[dict]:
        """Get all chats for a user"""
        db = SessionLocal()
        try:
            chats = chat_crud.get_user_chats(db, user_id, limit)
            return [
                {
                    "chat_id": chat.chat_id,
                    "title": chat.title,
                    "created_at": chat.created_at.isoformat(),
                    "updated_at": chat.updated_at.isoformat()
                }
                for chat in chats
            ]
        finally:
            db.close()

