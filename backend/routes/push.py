"""
Push notification registration routes.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db_session
from auth.dependencies import get_current_user_id
from services.push_notifications import (
    register_device_token,
    unregister_device_token,
    send_push_notification,
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


@router.post("/register")
async def register_token(
    req: RegisterTokenRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
):
    await register_device_token(db, user_id, req.token, req.platform)
    return {"success": True, "message": "Device token registered"}


@router.post("/unregister")
async def unregister_token(
    req: UnregisterTokenRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
):
    await unregister_device_token(db, req.token)
    return {"success": True, "message": "Device token removed"}


@router.post("/test")
async def test_push(
    req: TestPushRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
):
    sent = await send_push_notification(db, user_id, req.title, req.body)
    return {"success": sent, "message": "Push sent" if sent else "No registered devices"}
