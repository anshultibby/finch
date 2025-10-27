"""
Chat service for managing chat sessions and interactions
"""
from typing import Dict, List, Any
from datetime import datetime
from agent import ChatAgent
from .context_manager import context_manager


class ChatService:
    """Service for handling chat operations"""
    
    def __init__(self):
        self.agent = ChatAgent()
        # In-memory storage for chat sessions (can be replaced with database later)
        self.sessions: Dict[str, List[Dict[str, Any]]] = {}
    
    async def send_message(
        self, 
        message: str, 
        session_id: str
    ) -> tuple[str, str, bool]:
        """
        Send a message and get agent response
        
        Args:
            message: User message content
            session_id: Session identifier
            
        Returns:
            Tuple of (response, timestamp, needs_auth)
        """
        # Initialize session if needed
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        
        # Add user message to history
        user_message = {
            "role": "user",
            "content": message,
            "timestamp": datetime.now().isoformat()
        }
        self.sessions[session_id].append(user_message)
        
        # Get context for this session
        context = context_manager.get_all_context(session_id)
        
        # Get agent response (with context for tools)
        # The agent now returns the full conversation with tool calls
        response, needs_auth, full_messages = await self.agent.process_message(
            message=message,
            chat_history=self.sessions[session_id],
            context=context,
            session_id=session_id
        )
        
        # Store the full conversation including tool calls and results
        # Replace the session history with the full messages (excluding system and user messages already stored)
        if full_messages:
            # Remove the last user message we just added since it's in full_messages
            self.sessions[session_id] = full_messages
        else:
            # Fallback: just add assistant response
            timestamp = datetime.now().isoformat()
            assistant_message = {
                "role": "assistant",
                "content": response,
                "timestamp": timestamp
            }
            self.sessions[session_id].append(assistant_message)
        
        timestamp = datetime.now().isoformat()
        return response, timestamp, needs_auth
    
    def get_session_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get chat history for a session"""
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")
        return self.sessions[session_id]
    
    def clear_session(self, session_id: str) -> bool:
        """Clear chat history for a session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False
    
    def session_exists(self, session_id: str) -> bool:
        """Check if session exists"""
        return session_id in self.sessions

