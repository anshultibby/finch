"""
Chat API routes
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import uuid
import asyncio
import json

from models import ChatMessage, ChatResponse
from modules import ChatService
from services.chat_title import generate_chat_title
from database import get_db_session
from crud import chat_async
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


class GenerateTitleRequest(BaseModel):
    """Request model for generating chat title"""
    chat_id: str
    first_message: str


class GenerateTitleResponse(BaseModel):
    """Response model for chat title generation"""
    title: str
    icon: str

# Initialize chat service
chat_service = ChatService()


@router.post("/stream")
async def send_chat_message_stream(chat_message: ChatMessage):
    """
    Send a chat message and receive streaming SSE events as tool calls are made
    
    This endpoint streams Server-Sent Events (SSE) with the following event types:
    - tool_call_start: When a tool call begins execution
    - tool_call_complete: When a tool call finishes
    - assistant_message: The final assistant response
    - done: Stream is complete
    - error: An error occurred
    
    Supports multimodal messages with optional image attachments.
    
    Returns:
        StreamingResponse with text/event-stream content type
    """
    try:
        # Validate required fields
        if not chat_message.user_id:
            raise HTTPException(status_code=400, detail="user_id is required")
        if not chat_message.chat_id:
            raise HTTPException(status_code=400, detail="chat_id is required")
        
        # Extract images if present (convert to list of dicts for service layer)
        images = None
        if chat_message.images:
            images = [{"data": img.data, "media_type": img.media_type} for img in chat_message.images]
        
        # Create streaming generator with explicit flushing
        async def event_generator():
            try:
                async for sse_data in chat_service.send_message_stream(
                    message=chat_message.message,
                    chat_id=chat_message.chat_id,
                    user_id=chat_message.user_id,
                    images=images
                ):
                    # Yield event immediately
                    yield sse_data
                    # Force flush by yielding empty string (hack to prevent buffering)
                    # This triggers uvicorn to send data immediately
                    await asyncio.sleep(0)  # Give control back to event loop
            except Exception as e:
                import traceback
                error_msg = str(e)
                tb = traceback.format_exc()
                logger.error(f"ERROR in stream: {error_msg}\nFull traceback:\n{tb}")
                # Send error event
                # Use string concatenation to avoid f-string interpreting JSON curly braces as format specs
                yield "event: error\ndata: " + json.dumps({'error': error_msg}) + "\n\n"
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable buffering in nginx
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_msg = str(e)
        logger.error(f"ERROR in stream endpoint: {error_msg}")
        logger.debug(f"Traceback:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{chat_id}")
async def get_chat_history(chat_id: str):
    """
    Retrieve chat history for a specific chat
    """
    try:
        messages = await chat_service.get_chat_history(chat_id)
        return {
            "chat_id": chat_id,
            "messages": messages
        }
    except ValueError:
        raise HTTPException(status_code=404, detail="Chat not found")


@router.get("/history/{chat_id}/display")
async def get_chat_history_display(chat_id: str):
    """
    Retrieve chat history formatted for UI display.
    Returns a structured format with grouped tool calls and filtered messages.
    """
    try:
        display_data = await chat_service.get_chat_history_for_display(chat_id)
        return {
            "chat_id": chat_id,
            **display_data
        }
    except ValueError:
        raise HTTPException(status_code=404, detail="Chat not found")


@router.delete("/history/{chat_id}")
async def clear_chat_history(chat_id: str):
    """
    Clear chat history for a specific chat
    """
    success = await chat_service.clear_chat(chat_id)
    return {"message": "Chat history cleared" if success else "Chat not found or already cleared"}


@router.get("/user/{user_id}/chats")
async def list_user_chats(user_id: str, limit: int = 50):
    """
    List all chats for a user
    """
    try:
        chats = await chat_service.get_user_chats(user_id, limit)
        return {
            "user_id": user_id,
            "chats": chats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create")
async def create_new_chat(data: dict):
    """
    Create a new chat for a user
    """
    user_id = data.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    
    try:
        chat_id = str(uuid.uuid4())
        # Actually create the chat in DB
        async with get_db_session() as db:
            await chat_async.create_chat(db, chat_id, user_id)
        return {"chat_id": chat_id}
    except Exception as e:
        import traceback
        logger.error(f"Failed to create chat: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-title", response_model=GenerateTitleResponse)
async def generate_title(request: GenerateTitleRequest):
    """
    Generate a title and icon for a chat based on the first message.
    Uses LLM to create a descriptive title and matching emoji.
    """
    try:
        # Generate title and icon using LLM
        title, icon = await generate_chat_title(request.first_message)
        
        # Update the chat in database
        async with get_db_session() as db:
            await chat_async.update_chat_title(db, request.chat_id, title, icon)
        
        return GenerateTitleResponse(title=title, icon=icon)
        
    except Exception as e:
        import traceback
        logger.error(f"Failed to generate title: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{chat_id}")
async def get_chat_status(chat_id: str):
    """
    Check if a chat is currently being processed by the backend.
    Used for reconnection logic to determine if streaming should resume.
    
    Returns:
        - is_processing: Whether the chat is currently being processed
        - last_activity: Timestamp of last activity
    """
    try:
        async with get_db_session() as db:
            # Check processing status and get last activity in parallel
            is_processing = await chat_async.is_chat_processing(db, chat_id)
            last_activity = await chat_async.get_last_activity_timestamp(db, chat_id)
        
        return {
            "is_processing": is_processing,
            "last_activity": last_activity or ""
        }
    except Exception as e:
        logger.error(f"Error checking chat status: {e}")
        # Return safe defaults on error
        return {
            "is_processing": False,
            "last_activity": ""
        }

