"""
Push notification service using Expo's push API.

No Firebase needed — Expo handles APNs/FCM token exchange.
Sends to https://exp.host/--/api/v2/push/send
"""
import logging
import httpx
from typing import Optional
from sqlalchemy import select, delete, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from models.user import DeviceToken, Notification

logger = logging.getLogger(__name__)

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


async def register_device_token(
    db: AsyncSession, user_id: str, token: str, platform: str
) -> None:
    stmt = pg_insert(DeviceToken).values(
        user_id=user_id, token=token, platform=platform
    ).on_conflict_do_update(
        index_elements=["token"],
        set_={"user_id": user_id, "platform": platform},
    )
    await db.execute(stmt)
    await db.commit()


async def unregister_device_token(db: AsyncSession, token: str) -> None:
    await db.execute(delete(DeviceToken).where(DeviceToken.token == token))
    await db.commit()


async def get_user_tokens(db: AsyncSession, user_id: str) -> list[DeviceToken]:
    result = await db.execute(
        select(DeviceToken).where(DeviceToken.user_id == user_id)
    )
    return list(result.scalars().all())


async def create_notification(
    db: AsyncSession,
    user_id: str,
    title: str,
    body: str,
    notif_type: str = "general",
    data: Optional[dict] = None,
) -> Notification:
    notif = Notification(
        user_id=user_id,
        title=title,
        body=body,
        type=notif_type,
        data=data,
    )
    db.add(notif)
    await db.commit()
    await db.refresh(notif)
    return notif


async def get_notifications(
    db: AsyncSession, user_id: str, limit: int = 50, unread_only: bool = False
) -> list[Notification]:
    q = select(Notification).where(Notification.user_id == user_id)
    if unread_only:
        q = q.where(Notification.read == False)
    q = q.order_by(Notification.created_at.desc()).limit(limit)
    result = await db.execute(q)
    return list(result.scalars().all())


async def get_unread_count(db: AsyncSession, user_id: str) -> int:
    result = await db.execute(
        select(func.count(Notification.id)).where(
            Notification.user_id == user_id, Notification.read == False
        )
    )
    return result.scalar() or 0


async def mark_notifications_read(
    db: AsyncSession, user_id: str, notification_ids: Optional[list[str]] = None
) -> int:
    q = update(Notification).where(Notification.user_id == user_id, Notification.read == False)
    if notification_ids:
        q = q.where(Notification.id.in_(notification_ids))
    q = q.values(read=True)
    result = await db.execute(q)
    await db.commit()
    return result.rowcount


async def send_push_notification(
    db: AsyncSession,
    user_id: str,
    title: str,
    body: str,
    data: Optional[dict] = None,
    notif_type: str = "general",
    persist: bool = True,
) -> bool:
    if persist:
        await create_notification(db, user_id, title, body, notif_type, data)

    tokens = await get_user_tokens(db, user_id)
    if not tokens:
        return False

    messages = []
    for dt in tokens:
        if not dt.token.startswith("ExponentPushToken"):
            continue
        msg = {
            "to": dt.token,
            "title": title,
            "body": body,
            "sound": "default",
            "badge": 1,
        }
        if data:
            msg["data"] = data
        messages.append(msg)

    if not messages:
        return False

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                EXPO_PUSH_URL,
                json=messages,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                timeout=10.0,
            )
            result = response.json()

            stale_tokens = []
            for i, ticket in enumerate(result.get("data", [])):
                if ticket.get("status") == "error":
                    detail = ticket.get("details", {})
                    if detail.get("error") == "DeviceNotRegistered":
                        stale_tokens.append(tokens[i].token)
                    logger.warning(
                        "Push failed for token %s: %s",
                        tokens[i].token[:20],
                        ticket.get("message"),
                    )

            for stale in stale_tokens:
                await unregister_device_token(db, stale)

            return any(
                t.get("status") == "ok" for t in result.get("data", [])
            )
    except Exception:
        logger.exception("Failed to send push notification")
        return False
