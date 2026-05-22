"""
Memory Store & Dreams Routes — user-scoped endpoints for the agent's
persistent memory store and dream (reflection) sessions.
"""
import asyncio
import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_async_db
from auth.dependencies import get_current_user_id
from pydantic import BaseModel
from typing import Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/store", tags=["store"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class StoreFileResponse(BaseModel):
    filename: str
    file_type: str
    content: Optional[str] = None
    updated_at: Optional[str] = None


class StoreFileUpdateRequest(BaseModel):
    content: str


class DreamResponse(BaseModel):
    id: str
    status: str
    trigger: str
    summary: Optional[str] = None
    self_score: Optional[int] = None
    output_diff: Optional[list] = None
    follow_ups: Optional[list] = None
    chat_ids: Optional[list] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    created_at: str


# ---------------------------------------------------------------------------
# Store endpoints
# ---------------------------------------------------------------------------

@router.get("/files")
async def list_store_files(
    db: AsyncSession = Depends(get_async_db),
    user_id: str = Depends(get_current_user_id),
):
    """List all files in the memory store. Syncs from sandbox first."""
    # Sync from sandbox so we always show the latest
    try:
        from services.store_sync import sync_store_files
        await sync_store_files(user_id)
    except Exception as e:
        logger.debug(f"Store sync during list failed (non-fatal): {e}")

    from crud.store import list_store_files as crud_list
    files = await crud_list(db, user_id)
    return [
        StoreFileResponse(
            filename=f.filename,
            file_type=f.file_type,
            updated_at=f.updated_at.isoformat() if f.updated_at else None,
        )
        for f in files
    ]


@router.get("/files/{path:path}")
async def read_store_file(
    path: str,
    db: AsyncSession = Depends(get_async_db),
    user_id: str = Depends(get_current_user_id),
):
    from crud.store import get_store_file
    filename = path if path.startswith("store/") else f"store/{path}"
    file = await get_store_file(db, user_id, filename)
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    return StoreFileResponse(
        filename=file.filename,
        file_type=file.file_type,
        content=file.content,
        updated_at=file.updated_at.isoformat() if file.updated_at else None,
    )


@router.put("/files/{path:path}")
async def update_store_file(
    path: str,
    body: StoreFileUpdateRequest,
    db: AsyncSession = Depends(get_async_db),
    user_id: str = Depends(get_current_user_id),
):
    from crud.store import upsert_store_file
    filename = path if path.startswith("store/") else f"store/{path}"
    file = await upsert_store_file(db, user_id, filename, content=body.content)

    # Also write to sandbox if available
    try:
        from modules.tools.implementations.code_execution import get_or_create_sandbox
        entry = await get_or_create_sandbox(user_id, envs={})
        abs_path = f"/home/user/{filename}"
        parent = "/".join(abs_path.split("/")[:-1])
        await entry.sbx.commands.run(f"mkdir -p {parent}", timeout=5)
        await entry.sbx.files.write(abs_path, body.content)
    except Exception as e:
        logger.debug(f"Failed to sync store edit to sandbox (non-fatal): {e}")

    return {"ok": True, "filename": file.filename}


# ---------------------------------------------------------------------------
# Dream endpoints
# ---------------------------------------------------------------------------

@router.get("/dreams")
async def list_dreams_endpoint(
    limit: int = 20,
    db: AsyncSession = Depends(get_async_db),
    user_id: str = Depends(get_current_user_id),
):
    from crud.store import list_dreams
    dreams = await list_dreams(db, user_id, limit=limit)
    return [
        DreamResponse(
            id=str(d.id),
            status=d.status,
            trigger=d.trigger,
            summary=d.summary,
            self_score=d.self_score,
            output_diff=d.output_diff,
            follow_ups=d.follow_ups,
            chat_ids=d.chat_ids,
            started_at=d.started_at.isoformat() if d.started_at else None,
            completed_at=d.completed_at.isoformat() if d.completed_at else None,
            created_at=d.created_at.isoformat(),
        )
        for d in dreams
    ]


@router.get("/dreams/{dream_id}")
async def get_dream_detail(
    dream_id: str,
    db: AsyncSession = Depends(get_async_db),
    user_id: str = Depends(get_current_user_id),
):
    from crud.store import get_dream
    dream = await get_dream(db, dream_id)
    if not dream or dream.user_id != user_id:
        raise HTTPException(status_code=404, detail="Dream not found")
    return DreamResponse(
        id=str(dream.id),
        status=dream.status,
        trigger=dream.trigger,
        summary=dream.summary,
        self_score=dream.self_score,
        output_diff=dream.output_diff,
        follow_ups=dream.follow_ups,
        chat_ids=dream.chat_ids,
        started_at=dream.started_at.isoformat() if dream.started_at else None,
        completed_at=dream.completed_at.isoformat() if dream.completed_at else None,
        created_at=dream.created_at.isoformat(),
    )


@router.get("/dreams/{dream_id}/transcript")
async def get_dream_transcript(
    dream_id: str,
    db: AsyncSession = Depends(get_async_db),
    user_id: str = Depends(get_current_user_id),
):
    """Get the full chat transcript of a dream session."""
    from crud.store import get_dream
    dream = await get_dream(db, dream_id)
    if not dream or dream.user_id != user_id:
        raise HTTPException(status_code=404, detail="Dream not found")
    return {"dream_id": dream_id, "transcript": dream.transcript or []}


@router.post("/dreams/trigger")
async def trigger_dream(
    db: AsyncSession = Depends(get_async_db),
    user_id: str = Depends(get_current_user_id),
):
    from services.dreaming import DreamingService
    dream_id = await DreamingService().trigger_dream(
        user_id=user_id,
        trigger_type="manual",
    )
    if not dream_id:
        raise HTTPException(status_code=429, detail="Dream already running or in cooldown")
    return {"dream_id": dream_id}


@router.get("/dreams/{dream_id}/stream")
async def stream_dream_progress(
    dream_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    """SSE stream of dream progress events."""
    from crud.store import get_dream
    from services.dreaming import subscribe_dream, unsubscribe_dream

    dream = await get_dream(db, dream_id)
    if not dream or dream.user_id != user_id:
        raise HTTPException(status_code=404, detail="Dream not found")

    if dream.status in ("completed", "failed"):
        async def done_stream():
            yield f"event: dream_{dream.status}\ndata: {json.dumps({'dream_id': dream_id, 'status': dream.status})}\n\n"
        return StreamingResponse(done_stream(), media_type="text/event-stream")

    queue = subscribe_dream(dream_id)
    HEARTBEAT_INTERVAL = 15

    async def event_generator():
        try:
            while True:
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=HEARTBEAT_INTERVAL)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
                    continue

                if item is None:
                    break

                event_type = item.get("event", "dream_progress")
                data = item.get("data", {})
                yield f"event: {event_type}\ndata: {json.dumps(data, default=str)}\n\n"

                if event_type in ("dream_completed", "dream_failed"):
                    break
        finally:
            unsubscribe_dream(dream_id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
