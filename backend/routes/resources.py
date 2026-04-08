"""
Resources API routes
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, delete
from core.database import get_async_db
from models.chat_models import Resource
from schemas import ResourceResponse, ResourceMetadata

router = APIRouter(prefix="/resources", tags=["resources"])


def _to_response(r: Resource) -> ResourceResponse:
    return ResourceResponse(
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


@router.get("/chat/{chat_id}", response_model=List[ResourceResponse])
async def get_chat_resources(chat_id: str, limit: int = 100, db: AsyncSession = Depends(get_async_db)):
    try:
        result = await db.execute(
            select(Resource).where(Resource.chat_id == chat_id)
            .order_by(Resource.created_at.desc()).limit(limit)
        )
        return [_to_response(r) for r in result.scalars().all()]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/{user_id}", response_model=List[ResourceResponse])
async def get_user_resources(user_id: str, limit: int = 100, db: AsyncSession = Depends(get_async_db)):
    try:
        result = await db.execute(
            select(Resource).where(Resource.user_id == user_id)
            .order_by(Resource.created_at.desc()).limit(limit)
        )
        return [_to_response(r) for r in result.scalars().all()]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{resource_id}", response_model=ResourceResponse)
async def get_resource(resource_id: str, db: AsyncSession = Depends(get_async_db)):
    try:
        result = await db.execute(select(Resource).where(Resource.id == resource_id))
        resource = result.scalar_one_or_none()
        if not resource:
            raise HTTPException(status_code=404, detail="Resource not found")
        return _to_response(resource)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{resource_id}")
async def delete_resource(resource_id: str, db: AsyncSession = Depends(get_async_db)):
    try:
        result = await db.execute(select(Resource).where(Resource.id == resource_id))
        resource = result.scalar_one_or_none()
        if not resource:
            raise HTTPException(status_code=404, detail="Resource not found")
        await db.delete(resource)
        return {"message": "Resource deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
