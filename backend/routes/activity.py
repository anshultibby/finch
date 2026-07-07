"""Agent activity feed + "while you were gone" recap.

- GET  /activity          -> paginated ledger of what the agent did
- GET  /activity/recap    -> aggregated recap since last seen (+ pending
                             approvals + next scheduled run)
- POST /activity/seen     -> the user viewed/dismissed the recap
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from auth.dependencies import get_current_user_id
from services import agent_events
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/activity", tags=["activity"])


@router.get("")
async def activity_feed(
    limit: int = Query(50, ge=1, le=100),
    before: Optional[datetime] = None,
    event_type: Optional[str] = Query(None, max_length=32),
    user_id: str = Depends(get_current_user_id),
):
    events = await agent_events.get_events(
        user_id, limit=limit, before=before, event_type=event_type
    )
    return {"events": events}


@router.get("/search-chats")
async def search_chats(
    q: str = Query(..., min_length=2, max_length=200),
    limit: int = Query(10, ge=1, le=25),
    user_id: str = Depends(get_current_user_id),
):
    """Content search across the user's past chats (including automation runs).

    The agent's long-term recall: heartbeat runs start fresh chats, so this is
    how they dig into earlier conversations when the ledger isn't enough.
    """
    from sqlalchemy import select, text
    from core.database import get_db_session
    from models.chat_models import Chat, ChatMessageDB

    async with get_db_session() as db:
        rows = (await db.execute(
            select(ChatMessageDB.chat_id, ChatMessageDB.content,
                   ChatMessageDB.timestamp, Chat.title)
            .join(Chat, Chat.chat_id == ChatMessageDB.chat_id)
            .where(
                Chat.user_id == user_id,
                ChatMessageDB.role.in_(("user", "assistant")),
                ChatMessageDB.content.ilike(f"%{q}%"),
            )
            .order_by(ChatMessageDB.timestamp.desc())
            .limit(limit * 3)  # a few per chat before dedup
        )).all()

    results, seen = [], set()
    for chat_id, content, ts, title in rows:
        if chat_id in seen:
            continue
        seen.add(chat_id)
        text_content = " ".join(str(content).split())
        i = text_content.lower().find(q.lower())
        start = max(0, i - 120)
        snippet = ("…" if start else "") + text_content[start:start + 300]
        results.append({
            "chat_id": chat_id,
            "title": title,
            "snippet": snippet,
            "timestamp": ts.isoformat() if ts else None,
        })
        if len(results) >= limit:
            break
    return {"results": results}


@router.get("/recap")
async def activity_recap(user_id: str = Depends(get_current_user_id)):
    # Fetched on every home open — our "user is active" signal. Gates (and
    # resumes) credit-spending automations like the heartbeat.
    await agent_events.touch_activity(user_id)
    return await agent_events.get_recap(user_id)


@router.post("/seen")
async def activity_seen(user_id: str = Depends(get_current_user_id)):
    await agent_events.mark_seen(user_id)
    return {"ok": True}


class InsightReport(BaseModel):
    """An insight the agent reports from a run (heartbeat or otherwise)."""
    title: str = Field(..., min_length=1, max_length=200)
    body: Optional[str] = Field(None, max_length=2000)
    alert: bool = False  # True = also push; reserve for genuinely urgent items
    chat_id: Optional[str] = Field(None, max_length=64)


@router.post("/insight")
async def report_insight(
    report: InsightReport,
    user_id: str = Depends(get_current_user_id),
):
    """Record an agent insight in the ledger; optionally push it as an alert."""
    await agent_events.record_event(
        user_id, "insight", report.title, body=report.body,
        data={"chat_id": report.chat_id, "alert": report.alert},
        source="heartbeat",
    )
    pushed = False
    if report.alert:
        try:
            from core.database import get_db_session
            from services.push_notifications import send_push_notification
            async with get_db_session() as db:
                pushed = await send_push_notification(
                    db, user_id,
                    title=report.title,
                    body=(report.body or report.title)[:180],
                    data={"chatId": report.chat_id} if report.chat_id else None,
                    notif_type="insight",
                )
        except Exception as e:
            logger.warning(f"Insight alert push failed for {user_id}: {e}")
    return {"recorded": True, "alerted": pushed}
