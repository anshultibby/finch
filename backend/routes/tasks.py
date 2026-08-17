"""
API for the agent's task board.

Read-only by design. The markdown file in the sandbox is the source of truth
(see models/tasks.py), so a write here would be a second writer racing the
agent for the same state. Users steer tasks by talking to the agent, which
edits the file; the change flows back through the sync hook.
"""
import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from auth.dependencies import get_current_user_id
from core.database import get_async_db
from models.tasks import AgentTask, TASK_STATUSES

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["tasks"])

# Open work first, then blocked, then everything concluded — the order someone
# scanning the board actually wants, rather than alphabetical or purely by date.
_STATUS_RANK = {"open": 0, "blocked": 1, "done": 2, "dropped": 3}


def _serialize(t: AgentTask, *, include_body: bool) -> dict:
    out = {
        "id": str(t.id),
        "slug": t.slug,
        "title": t.title or t.slug,
        "status": t.status,
        "symbols": t.symbols or [],
        "opened_on": t.opened_on.isoformat() if t.opened_on else None,
        "review_on": t.review_on.isoformat() if t.review_on else None,
        "chat_id": str(t.chat_id) if t.chat_id else None,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None,
    }
    if include_body:
        out["body"] = t.body
    return out


@router.get("")
async def list_tasks(
    status: Optional[str] = Query(None, description="Filter to one status"),
    due_by: Optional[date] = Query(None, description="Only tasks due for review on/before this date"),
    symbol: Optional[str] = Query(None, description="Only tasks touching this ticker"),
    db: AsyncSession = Depends(get_async_db),
    user_id: str = Depends(get_current_user_id),
):
    """The board. Bodies are omitted — this is the index layer, so it stays
    cheap to render however many tasks have accumulated."""
    if status and status not in TASK_STATUSES:
        raise HTTPException(status_code=400, detail=f"status must be one of {list(TASK_STATUSES)}")
    try:
        stmt = select(AgentTask).where(AgentTask.user_id == user_id)
        if status:
            stmt = stmt.where(AgentTask.status == status)
        if due_by:
            stmt = stmt.where(AgentTask.review_on.isnot(None), AgentTask.review_on <= due_by)
        if symbol:
            stmt = stmt.where(AgentTask.symbols.contains([symbol.upper()]))

        rows = (await db.execute(stmt)).scalars().all()
        rows.sort(key=lambda t: (
            _STATUS_RANK.get(t.status, 9),
            t.review_on or date.max,
            t.updated_at or date.min,
        ))
        counts = {s: sum(1 for t in rows if t.status == s) for s in TASK_STATUSES}
        return {
            "tasks": [_serialize(t, include_body=False) for t in rows],
            "counts": counts,
        }
    except Exception as e:
        logger.error(f"Error listing tasks for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to list tasks")


@router.get("/{slug}")
async def get_task(
    slug: str,
    db: AsyncSession = Depends(get_async_db),
    user_id: str = Depends(get_current_user_id),
):
    """One task in full, including the markdown body."""
    try:
        task = (await db.execute(
            select(AgentTask).where(
                AgentTask.user_id == user_id,
                sa_func.lower(AgentTask.slug) == slug.strip().lower(),
            )
        )).scalars().first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return _serialize(task, include_body=True)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching task {slug}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch task")
