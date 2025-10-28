"""
Chat service for managing chat sessions and interactions
"""
from typing import List, Any, Optional
from datetime import datetime
import json
from agent import ChatAgent
from .context_manager import context_manager
from database import SessionLocal
from crud import chat as chat_crud


class ChatService:
    """Service for handling chat operations"""
    
    def __init__(self):
        self.agent = ChatAgent()
    
    async def send_message(
        self, 
        message: str, 
        chat_id: str,
        user_id: str
    ) -> tuple[str, str, bool]:
        """
        Send a message and get agent response
        
        Args:
            message: User message content
            chat_id: Chat identifier
            user_id: User identifier (for SnapTrade tools)
            
        Returns:
            Tuple of (response, timestamp, needs_auth)
        """
        db = SessionLocal()
        try:
            # Ensure chat exists
            db_chat = chat_crud.get_chat(db, chat_id)
            if not db_chat:
                # Create new chat
                chat_crud.create_chat(db, chat_id, user_id)
            
            # Get existing chat history and deserialize
            db_messages = chat_crud.get_chat_messages(db, chat_id)
            chat_history = []
            for msg in db_messages:
                # Deserialize content if it's JSON (for tool messages)
                content = msg.content
                try:
                    parsed_content = json.loads(content)
                    # If it successfully parses as JSON, it might be tool data
                    if isinstance(parsed_content, dict):
                        message_dict = {
                            "role": msg.role,
                            "content": parsed_content.get("content", ""),
                            "timestamp": msg.timestamp.isoformat()
                        }
                        # Add tool-specific fields if present
                        if "tool_calls" in parsed_content:
                            message_dict["tool_calls"] = parsed_content["tool_calls"]
                        if "tool_call_id" in parsed_content:
                            message_dict["tool_call_id"] = parsed_content["tool_call_id"]
                            message_dict["name"] = parsed_content.get("name", "")
                        chat_history.append(message_dict)
                    else:
                        # Plain text content
                        chat_history.append({
                            "role": msg.role,
                            "content": content,
                            "timestamp": msg.timestamp.isoformat()
                        })
                except (json.JSONDecodeError, TypeError):
                    # Not JSON, treat as plain text
                    chat_history.append({
                        "role": msg.role,
                        "content": content,
                        "timestamp": msg.timestamp.isoformat()
                    })
            
            # Get context for this user (using user_id for SnapTrade)
            context = context_manager.get_all_context(user_id)
            
            # Get agent response with full conversation including tool calls
            response, needs_auth, full_messages = await self.agent.process_message(
                message=message,
                chat_history=chat_history,
                context=context,
                session_id=user_id  # Pass user_id as session_id for tools
            )
            
            # Store ALL new messages including user message, tool calls, and assistant responses
            # full_messages contains the complete conversation including what we just processed
            # We need to store only the NEW messages (after the existing history)
            start_index = len(db_messages)
            sequence = start_index
            
            final_timestamp = None
            for msg in full_messages[start_index:]:
                # Serialize content based on message type
                if msg["role"] == "tool" or "tool_calls" in msg:
                    # Store complex messages as JSON
                    content_to_store = json.dumps({
                        "content": msg.get("content", ""),
                        "tool_calls": msg.get("tool_calls"),
                        "tool_call_id": msg.get("tool_call_id"),
                        "name": msg.get("name")
                    })
                else:
                    # Store simple text messages as-is
                    content_to_store = msg.get("content", "")
                
                stored_msg = chat_crud.create_message(
                    db, chat_id, msg["role"], content_to_store, sequence
                )
                sequence += 1
                final_timestamp = stored_msg.timestamp.isoformat()
            
            return response, final_timestamp or datetime.now().isoformat(), needs_auth
            
        finally:
            db.close()
    
    def get_chat_history(self, chat_id: str) -> List[dict]:
        """Get chat history for a chat, including tool calls"""
        db = SessionLocal()
        try:
            messages = chat_crud.get_chat_messages(db, chat_id)
            history = []
            for msg in messages:
                # Try to deserialize JSON content (for tool messages)
                try:
                    parsed_content = json.loads(msg.content)
                    if isinstance(parsed_content, dict):
                        # Reconstruct the full message with tool data
                        message_dict = {
                            "role": msg.role,
                            "content": parsed_content.get("content", ""),
                            "timestamp": msg.timestamp.isoformat()
                        }
                        # Add tool-specific fields if present
                        if parsed_content.get("tool_calls"):
                            message_dict["tool_calls"] = parsed_content["tool_calls"]
                        if parsed_content.get("tool_call_id"):
                            message_dict["tool_call_id"] = parsed_content["tool_call_id"]
                            message_dict["name"] = parsed_content.get("name", "")
                        history.append(message_dict)
                    else:
                        # Plain text that happened to be JSON
                        history.append({
                            "role": msg.role,
                            "content": msg.content,
                            "timestamp": msg.timestamp.isoformat()
                        })
                except (json.JSONDecodeError, TypeError):
                    # Not JSON, plain text message
                    history.append({
                        "role": msg.role,
                        "content": msg.content,
                        "timestamp": msg.timestamp.isoformat()
                    })
            return history
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

