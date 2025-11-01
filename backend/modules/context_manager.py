"""
Context manager for storing user-specific variables that aren't visible to the model
These include credentials, user data, and other sensitive information
"""
from typing import Dict, Any, Optional
from datetime import datetime


class ContextManager:
    """
    Manages context variables per user
    Context variables are passed to tools but NOT visible to the LLM
    """
    
    def __init__(self):
        # Store context per user_id
        self._contexts: Dict[str, Dict[str, Any]] = {}
    
    def set_context(self, user_id: str, key: str, value: Any) -> None:
        """Set a context variable for a user"""
        if user_id not in self._contexts:
            self._contexts[user_id] = {}
        
        self._contexts[user_id][key] = value
        self._contexts[user_id]["last_updated"] = datetime.now().isoformat()
    
    def get_context(self, user_id: str, key: str, default: Any = None) -> Any:
        """Get a context variable for a user"""
        if user_id not in self._contexts:
            return default
        return self._contexts[user_id].get(key, default)
    
    def get_all_context(self, user_id: str) -> Dict[str, Any]:
        """Get all context variables for a user"""
        return self._contexts.get(user_id, {})
    
    def delete_context(self, user_id: str, key: str) -> bool:
        """Delete a specific context variable"""
        if user_id in self._contexts and key in self._contexts[user_id]:
            del self._contexts[user_id][key]
            return True
        return False
    
    def clear_user(self, user_id: str) -> None:
        """Clear all context for a user"""
        if user_id in self._contexts:
            del self._contexts[user_id]
    
    def has_robinhood_credentials(self, user_id: str) -> bool:
        """Check if Robinhood credentials are set for this user"""
        context = self.get_all_context(user_id)
        return "robinhood_username" in context and "robinhood_password" in context


# Global context manager instance
context_manager = ContextManager()

