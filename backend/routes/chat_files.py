"""
Chat Files Routes - API endpoints for file management
"""
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from database import get_db
from crud.chat_files import (
    list_chat_files,
    get_chat_file,
    delete_chat_file as delete_file_crud
)
from pydantic import BaseModel
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat-files", tags=["chat-files"])


class ChatFileResponse(BaseModel):
    """Chat file metadata"""
    id: str
    filename: str
    file_type: str
    size_bytes: int
    description: Optional[str]
    created_at: str
    updated_at: str


@router.get("/{chat_id}", response_model=List[ChatFileResponse])
async def get_chat_files(
    chat_id: str,
    db: Session = Depends(get_db)
):
    """
    Get all files for a chat
    
    Returns list of file metadata (not content - use download endpoint)
    """
    try:
        files = list_chat_files(db=db, chat_id=chat_id)
        
        return [
            ChatFileResponse(
                id=f.id,
                filename=f.filename,
                file_type=f.file_type,
                size_bytes=f.size_bytes,
                description=f.description,
                created_at=f.created_at.isoformat(),
                updated_at=f.updated_at.isoformat()
            )
            for f in files
        ]
    
    except Exception as e:
        logger.error(f"Error getting chat files: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{chat_id}/download/{filename}")
async def download_chat_file(
    chat_id: str,
    filename: str,
    db: Session = Depends(get_db)
):
    """
    Download a specific file from chat
    
    Returns file content with appropriate Content-Type header
    """
    try:
        file_obj = get_chat_file(db=db, chat_id=chat_id, filename=filename)
        
        if not file_obj:
            raise HTTPException(status_code=404, detail=f"File '{filename}' not found")
        
        # Set Content-Type based on file type
        content_type_map = {
            "python": "text/x-python",
            "markdown": "text/markdown",
            "text": "text/plain",
            "csv": "text/csv",
            "json": "application/json",
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "gif": "image/gif",
            "svg": "image/svg+xml",
            "webp": "image/webp"
        }
        
        content_type = content_type_map.get(file_obj.file_type, "text/plain")
        
        # For images, use inline disposition so they display in browser
        is_image = file_obj.file_type in ["png", "jpg", "jpeg", "gif", "svg", "webp"]
        disposition = "inline" if is_image else "attachment"
        
        return Response(
            content=file_obj.content,
            media_type=content_type,
            headers={
                "Content-Disposition": f'{disposition}; filename="{filename}"'
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{chat_id}/{filename}")
async def delete_chat_file(
    chat_id: str,
    filename: str,
    db: Session = Depends(get_db)
):
    """Delete a file from chat"""
    try:
        success = delete_file_crud(db=db, chat_id=chat_id, filename=filename)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"File '{filename}' not found")
        
        return {"success": True, "message": f"Deleted {filename}"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting file: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

