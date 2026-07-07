"""Agent activity feed + "while you were gone" recap.

- GET  /activity          -> paginated ledger of what the agent did
- GET  /activity/recap    -> aggregated recap since last seen (+ pending
                             approvals + next scheduled run)
- POST /activity/seen     -> the user viewed/dismissed the recap
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query

from auth.dependencies import get_current_user_id
from services import agent_events

router = APIRouter(prefix="/activity", tags=["activity"])


@router.get("")
async def activity_feed(
    limit: int = Query(50, ge=1, le=100),
    before: Optional[datetime] = None,
    user_id: str = Depends(get_current_user_id),
):
    events = await agent_events.get_events(user_id, limit=limit, before=before)
    return {"events": events}


@router.get("/recap")
async def activity_recap(user_id: str = Depends(get_current_user_id)):
    return await agent_events.get_recap(user_id)


@router.post("/seen")
async def activity_seen(user_id: str = Depends(get_current_user_id)):
    await agent_events.mark_seen(user_id)
    return {"ok": True}
