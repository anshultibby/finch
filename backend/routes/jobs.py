"""
Scheduled jobs API — list / create / cancel jobs. Jobs themselves are
file-backed (see services/job_scheduler); job runs authenticate via
backend-minted sessions (see services/job_auth).
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from auth.dependencies import get_current_user_id
from schemas.jobs import JobCreate, JobUpdate, Job, JobList
from services import job_scheduler
from services.job_auth import has_token
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])


class RegisterTokenRequest(BaseModel):
    refresh_token: str


@router.post("/register-token")
async def register_token(body: RegisterTokenRequest, user_id: str = Depends(get_current_user_id)):
    """Deprecated no-op, kept so shipped clients don't 404. The backend mints
    its own Supabase session per user now; storing (and later spending) the
    caller's refresh token here is what used to log users out — the client's
    copy became a stale ancestor in the same token family, and Supabase's
    reuse detection revoked the whole family on their next silent refresh."""
    return {"ok": True}


@router.get("/usage")
async def routine_usage(user_id: str = Depends(get_current_user_id)):
    """Plan limits + current usage for the Routines screen (active count, runs
    today, per-plan caps). Static path — declared before /{job_id} routes."""
    return await job_scheduler.routine_usage(user_id)


@router.get("", response_model=JobList)
async def list_jobs(user_id: str = Depends(get_current_user_id)):
    """One query. Deliberately no provisioning work on this path.

    This used to backfill day_trading_nightly on every GET — an is_connected()
    call plus an upsert, which turned a read into four sequential DB round trips
    (~4s observed) and rewrote the job row every time the page was opened. Both
    Robinhood connect paths already call ensure_day_trading_nightly(), so the
    backfill was only ever covering users who connected before system jobs
    existed, at the cost of every page load since.
    """
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
