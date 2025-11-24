"""
Chat API routes
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import uuid
import asyncio

from models import ChatMessage, ChatResponse
from modules import ChatService
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

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
    
    Returns:
        StreamingResponse with text/event-stream content type
    """
    try:
        # Validate required fields
        if not chat_message.user_id:
            raise HTTPException(status_code=400, detail="user_id is required")
        if not chat_message.chat_id:
            raise HTTPException(status_code=400, detail="chat_id is required")
        
        # Create streaming generator with explicit flushing
        async def event_generator():
            try:
                async for sse_data in chat_service.send_message_stream(
                    message=chat_message.message,
                    chat_id=chat_message.chat_id,
                    user_id=chat_message.user_id
                ):
                    # Yield event immediately
                    yield sse_data
                    # Force flush by yielding empty string (hack to prevent buffering)
                    # This triggers uvicorn to send data immediately
                    await asyncio.sleep(0)  # Give control back to event loop
            except Exception as e:
                import traceback
                error_msg = str(e)
                logger.error(f"ERROR in stream: {error_msg}")
                logger.debug(f"Traceback:\n{traceback.format_exc()}")
                # Send error event
                import json
                yield f"event: error\ndata: {json.dumps({'error': error_msg})}\n\n"
        
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

