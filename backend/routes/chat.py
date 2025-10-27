"""
Chat API routes
"""
from fastapi import APIRouter, HTTPException
import uuid

from models import ChatMessage, ChatResponse
from modules import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])

# Initialize chat service
chat_service = ChatService()


@router.post("", response_model=ChatResponse)
async def send_chat_message(chat_message: ChatMessage):
    """
    Send a chat message and receive a response from the AI agent
    """
    try:
        # Create or retrieve session
        session_id = chat_message.session_id or str(uuid.uuid4())
        
        # Process message through chat service
        response, timestamp, needs_auth = await chat_service.send_message(
            message=chat_message.message,
            session_id=session_id
        )
        
        return ChatResponse(
            response=response,
            session_id=session_id,
            timestamp=timestamp,
            needs_auth=needs_auth
        )
    
    except Exception as e:
        import traceback
        error_msg = str(e)
        print(f"❌ ERROR in chat route: {error_msg}", flush=True)
        print(f"❌ Traceback:\n{traceback.format_exc()}", flush=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{session_id}")
async def get_chat_history(session_id: str):
    """
    Retrieve chat history for a specific session
    """
    try:
        messages = chat_service.get_session_history(session_id)
        return {
            "session_id": session_id,
            "messages": messages
        }
    except ValueError:
        raise HTTPException(status_code=404, detail="Session not found")


@router.delete("/history/{session_id}")
async def clear_chat_history(session_id: str):
    """
    Clear chat history for a specific session
    """
    success = chat_service.clear_session(session_id)
    if success:
        return {"message": "Chat history cleared"}
    else:
        return {"message": "Session not found or already cleared"}

