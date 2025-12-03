"""
Resources API routes
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from sqlalchemy.orm import Session
from database import get_db
from crud import resource as resource_crud
from models import ResourceResponse, ResourceMetadata

router = APIRouter(prefix="/resources", tags=["resources"])


@router.get("/chat/{chat_id}", response_model=List[ResourceResponse])
async def get_chat_resources(chat_id: str, limit: int = 100, db: Session = Depends(get_db)):
    """
    Get all resources for a chat
    """
    try:
        resources = resource_crud.get_chat_resources(db, chat_id, limit)
        
        return [
            ResourceResponse(
                id=r.id,
                chat_id=r.chat_id,
                user_id=r.user_id,
                tool_name=r.tool_name,
                resource_type=r.resource_type,
                title=r.title,
                data=r.data,
                metadata=ResourceMetadata(**r.resource_metadata) if r.resource_metadata else None,
                created_at=r.created_at.isoformat()
            )
            for r in resources
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/{user_id}", response_model=List[ResourceResponse])
async def get_user_resources(user_id: str, limit: int = 100, db: Session = Depends(get_db)):
    """
    Get all resources for a user across all chats
    """
    try:
        resources = resource_crud.get_user_resources(db, user_id, limit)
        
        return [
            ResourceResponse(
                id=r.id,
                chat_id=r.chat_id,
                user_id=r.user_id,
                tool_name=r.tool_name,
                resource_type=r.resource_type,
                title=r.title,
                data=r.data,
                metadata=ResourceMetadata(**r.resource_metadata) if r.resource_metadata else None,
                created_at=r.created_at.isoformat()
            )
            for r in resources
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{resource_id}", response_model=ResourceResponse)
async def get_resource(resource_id: str, db: Session = Depends(get_db)):
    """
    Get a specific resource by ID
    """
    try:
        resource = resource_crud.get_resource(db, resource_id)
        
        if not resource:
            raise HTTPException(status_code=404, detail="Resource not found")
        
        return ResourceResponse(
            id=resource.id,
            chat_id=resource.chat_id,
            user_id=resource.user_id,
            tool_name=resource.tool_name,
            resource_type=resource.resource_type,
            title=resource.title,
            data=resource.data,
            metadata=ResourceMetadata(**resource.resource_metadata) if resource.resource_metadata else None,
            created_at=resource.created_at.isoformat()
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{resource_id}")
async def delete_resource(resource_id: str, db: Session = Depends(get_db)):
    """
    Delete a resource
    """
    try:
        success = resource_crud.delete_resource(db, resource_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Resource not found")
        
        return {"message": "Resource deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

