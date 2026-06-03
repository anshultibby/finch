"""
Push notification registration and notification history routes.
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_async_db
from auth.dependencies import get_current_user_id
from services.push_notifications import (
    register_device_token,
    unregister_device_token,
    send_push_notification,
    get_notifications,
    get_unread_count,
    mark_notifications_read,
)

router = APIRouter(prefix="/push", tags=["push"])


class RegisterTokenRequest(BaseModel):
    token: str
    platform: str  # 'ios' | 'android' | 'web'


class UnregisterTokenRequest(BaseModel):
    token: str


class TestPushRequest(BaseModel):
    title: str = "Test Notification"
    body: str = "This is a test push notification from Finch."


class MarkReadRequest(BaseModel):
    notification_ids: Optional[list[str]] = None


@router.post("/register")
async def register_token(
    req: RegisterTokenRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    await register_device_token(db, user_id, req.token, req.platform)
    return {"success": True, "message": "Device token registered"}


@router.post("/unregister")
async def unregister_token(
    req: UnregisterTokenRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    await unregister_device_token(db, req.token)
    return {"success": True, "message": "Device token removed"}


@router.post("/test")
async def test_push(
    req: TestPushRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    sent = await send_push_notification(db, user_id, req.title, req.body)
    return {"success": sent, "message": "Push sent" if sent else "No registered devices"}


@router.get("/notifications")
async def list_notifications(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
    limit: int = Query(50, le=100),
    unread_only: bool = Query(False),
):
    notifications = await get_notifications(db, user_id, limit, unread_only)
    return {
        "notifications": [
            {
                "id": str(n.id),
                "title": n.title,
                "body": n.body,
                "type": n.type,
                "data": n.data,
                "read": n.read,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in notifications
        ]
    }


@router.get("/notifications/count")
async def unread_count(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    count = await get_unread_count(db, user_id)
    return {"unread_count": count}


@router.post("/notifications/read")
async def mark_read(
    req: MarkReadRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    updated = await mark_notifications_read(db, user_id, req.notification_ids)
    return {"success": True, "updated": updated}
