"""
Scheduled jobs API — register the per-user token (so jobs run as the user),
and list / create / cancel jobs. Jobs themselves are file-backed (see
services/job_scheduler).
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from auth.dependencies import get_current_user_id
from schemas.jobs import JobCreate, JobUpdate, Job, JobList
from services import job_scheduler
from services.job_auth import store_refresh_token, has_token
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])


class RegisterTokenRequest(BaseModel):
    refresh_token: str


@router.post("/register-token")
async def register_token(body: RegisterTokenRequest, user_id: str = Depends(get_current_user_id)):
    """Store the caller's Supabase refresh token so scheduled jobs can run as them."""
    if not body.refresh_token:
        raise HTTPException(status_code=400, detail="refresh_token required")
    await store_refresh_token(user_id, body.refresh_token)
    return {"ok": True}


@router.get("", response_model=JobList)
async def list_jobs(user_id: str = Depends(get_current_user_id)):
    # Backfill built-in automations for users who connected Robinhood before
    # system jobs existed. Idempotent and pause-respecting, so safe on a GET.
    try:
        from services import robinhood_auth
        if await robinhood_auth.is_connected(user_id):
            from services.system_jobs import ensure_day_trading_nightly
            await ensure_day_trading_nightly(user_id)
    except Exception as e:
        logger.warning(f"System-job backfill failed for {user_id}: {e}")
    return await job_scheduler.list_jobs(user_id)


@router.post("", response_model=Job)
async def create_job(body: JobCreate, user_id: str = Depends(get_current_user_id)):
    try:
        return await job_scheduler.create_job(user_id, body)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.patch("/{job_id}", response_model=Job)
async def update_job(job_id: str, body: JobUpdate, user_id: str = Depends(get_current_user_id)):
    try:
        job = await job_scheduler.update_job(user_id, job_id, body)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.delete("/{job_id}")
async def cancel_job(job_id: str, user_id: str = Depends(get_current_user_id)):
    try:
        ok = await job_scheduler.cancel_job(user_id, job_id)
    except ValueError as e:  # system job — pausable, not cancellable
        raise HTTPException(status_code=409, detail=str(e))
    if not ok:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"ok": True}


@router.post("/{job_id}/pause")
async def pause_job(job_id: str, user_id: str = Depends(get_current_user_id)):
    ok = await job_scheduler.set_status(user_id, job_id, "paused")
    if not ok:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"ok": True}


@router.post("/{job_id}/resume")
async def resume_job(job_id: str, user_id: str = Depends(get_current_user_id)):
    ok = await job_scheduler.set_status(user_id, job_id, "pending")
    if not ok:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"ok": True}


@router.post("/pause-all")
async def pause_all(user_id: str = Depends(get_current_user_id)):
    return {"paused": await job_scheduler.pause_all(user_id)}


@router.post("/resume-all")
async def resume_all(user_id: str = Depends(get_current_user_id)):
    return {"resumed": await job_scheduler.resume_all(user_id)}


@router.get("/status")
async def status(user_id: str = Depends(get_current_user_id)):
    """Whether this user has a stored token (jobs can run authenticated)."""
    return {"has_token": await has_token(user_id)}
