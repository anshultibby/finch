"""
Context manager for storing user-specific variables that aren't visible to the model
These include credentials, session data, and other sensitive information
"""
from typing import Dict, Any, Optional
from datetime import datetime


class ContextManager:
    """
    Manages context variables per session
    Context variables are passed to tools but NOT visible to the LLM
    """
    
    def __init__(self):
        # Store context per session_id
        self._contexts: Dict[str, Dict[str, Any]] = {}
    
    def set_context(self, session_id: str, key: str, value: Any) -> None:
        """Set a context variable for a session"""
        if session_id not in self._contexts:
            self._contexts[session_id] = {}
        
        self._contexts[session_id][key] = value
        self._contexts[session_id]["last_updated"] = datetime.now().isoformat()
    
    def get_context(self, session_id: str, key: str, default: Any = None) -> Any:
        """Get a context variable for a session"""
        if session_id not in self._contexts:
            return default
        return self._contexts[session_id].get(key, default)
    
    def get_all_context(self, session_id: str) -> Dict[str, Any]:
        """Get all context variables for a session"""
        return self._contexts.get(session_id, {})
    
    def delete_context(self, session_id: str, key: str) -> bool:
        """Delete a specific context variable"""
        if session_id in self._contexts and key in self._contexts[session_id]:
            del self._contexts[session_id][key]
            return True
        return False
    
    def clear_session(self, session_id: str) -> None:
        """Clear all context for a session"""
        if session_id in self._contexts:
            del self._contexts[session_id]
    
    def has_robinhood_credentials(self, session_id: str) -> bool:
        """Check if Robinhood credentials are set for this session"""
        context = self.get_all_context(session_id)
        return "robinhood_username" in context and "robinhood_password" in context


# Global context manager instance
context_manager = ContextManager()

