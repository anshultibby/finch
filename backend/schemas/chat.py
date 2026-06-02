"""
Chat-related Pydantic models (OpenAI format)
"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class ImageAttachment(BaseModel):
    """Image attachment for multimodal messages"""
    data: str  # Base64-encoded image data
    media_type: str = "image/png"  # MIME type (image/png, image/jpeg, etc.)


class ChatMessage(BaseModel):
    """Request model for sending a chat message"""
    message: str
    user_id: Optional[str] = None  # Supabase user ID
    chat_id: Optional[str] = None
    images: Optional[List[ImageAttachment]] = None  # Optional image attachments for multimodal
    skills: Optional[List[str]] = None  # Skill IDs manually selected for this turn
    page_context: Optional[Dict[str, Any]] = None  # Context from the page the user is viewing
    model: Optional[str] = None  # Per-chat LLM model selection (litellm id); persisted on the chat


class ToolCall(BaseModel):
    """Tool call structure (OpenAI format)"""
    id: str
    type: str = "function"
    function: Dict[str, Any]  # Contains 'name' and 'arguments'



