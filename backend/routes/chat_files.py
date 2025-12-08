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
        logger.info(f"Attempting to download file: {filename} from chat: {chat_id}")
        file_obj = get_chat_file(db=db, chat_id=chat_id, filename=filename)
        
        if not file_obj:
            # Log all available files in this chat for debugging
            from crud.chat_files import list_chat_files as crud_list_chat_files
            all_files = crud_list_chat_files(db=db, chat_id=chat_id)
            logger.warning(f"File '{filename}' not found in chat {chat_id}. Available files: {[f.filename for f in all_files]}")
            raise HTTPException(status_code=404, detail=f"File '{filename}' not found")
        
        # Set Content-Type based on file type
        content_type_map = {
            "python": "text/x-python",
            "markdown": "text/markdown",
            "text": "text/plain",
            "csv": "text/csv",
            "json": "application/json",
            "image": "image/png"  # Generic image type, will be refined below
        }
        
        # Determine if this is an image file
        is_image = file_obj.file_type == "image"
        
        # For images, determine specific content type from filename extension
        if is_image:
            if filename.lower().endswith('.png'):
                content_type = "image/png"
            elif filename.lower().endswith(('.jpg', '.jpeg')):
                content_type = "image/jpeg"
            elif filename.lower().endswith('.gif'):
                content_type = "image/gif"
            elif filename.lower().endswith('.svg'):
                content_type = "image/svg+xml"
            elif filename.lower().endswith('.webp'):
                content_type = "image/webp"
            else:
                content_type = "image/png"  # Default to PNG
            disposition = "inline"
        else:
            content_type = content_type_map.get(file_obj.file_type, "text/plain")
            disposition = "attachment"
        
        # Decode base64 content for binary files (images)
        content = file_obj.content
        if is_image:
            import base64
            try:
                # Images are stored as base64-encoded strings in the database
                content = base64.b64decode(content)
                logger.info(f"Decoded base64 image: {filename} ({len(content)} bytes)")
            except Exception as e:
                logger.error(f"Failed to decode base64 image {filename}: {str(e)}")
                # If decode fails, try returning as-is (might be raw bytes already)
        
        return Response(
            content=content,
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

