"""
Scheduled job service (Postgres-backed).

A job is a message + planned execution time (+ optional recurrence and context
file paths). The waker claims due jobs with row-locking (FOR UPDATE SKIP LOCKED)
so they never double-run, then runs each by sending its message to the agent —
*as the user* (via a refreshed access token), so authenticated tools work.

Limits per user: RECURRING_LIMIT recurring + ONEOFF_LIMIT one-off active jobs.
Priority is a column (0 = highest); the waker orders due jobs by it.
"""
import uuid
import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from sqlalchemy import select, func, update

from core.database import get_db_session
from models.jobs import ScheduledJob
from schemas.jobs import Job, JobCreate, JobUpdate, JobList
from utils.logger import get_logger

logger = get_logger(__name__)

RECURRING_LIMIT = 5
ONEOFF_LIMIT = 10
ACTIVE = ("pending", "running")
CLAIM_BATCH = 25


def _now() -> datetime:
    return datetime.now(timezone.utc)


def next_occurrence(after: datetime, recurrence: str) -> datetime:
    if recurrence == "hourly":
        return after + timedelta(hours=1)
    if recurrence == "weekly":
        return after + timedelta(weeks=1)
    if recurrence == "weekdays":
        nxt = after + timedelta(days=1)
        while nxt.weekday() >= 5:
            nxt += timedelta(days=1)
        return nxt
    return after + timedelta(days=1)  # daily / default


def _advance_past_now(run_at: datetime, recurrence: str) -> datetime:
    """Next occurrence strictly in the future — a backlog yields ONE run, not a
    burst catching up every missed slot."""
    nxt = next_occurrence(run_at, recurrence)
    now = _now()
    guard = 0
    while nxt <= now and guard < 10000:
        nxt = next_occurrence(nxt, recurrence)
        guard += 1
    return nxt


def _to_dto(row: ScheduledJob) -> Job:
    return Job(
        id=row.id, user_id=row.user_id, name=row.name, message=row.message,
        run_at=row.run_at, recurrence=row.recurrence, priority=row.priority,
        status=row.status, created_at=row.created_at, last_run_at=row.last_run_at,
        run_count=row.run_count, chat_id=row.chat_id,
        context_paths=row.context_paths or [], last_error=row.last_error,
    )


# ── CRUD ─────────────────────────────────────────────────────────────────────

async def list_jobs(user_id: str) -> JobList:
    async with get_db_session() as db:
        rows = (await db.execute(
            select(ScheduledJob).where(ScheduledJob.user_id == user_id)
            .order_by(ScheduledJob.priority, ScheduledJob.run_at)
        )).scalars().all()
    jobs = [_to_dto(r) for r in rows]
    active = [j for j in jobs if j.status in ACTIVE]
    recurring = sum(1 for j in active if j.is_recurring)
    oneoff = sum(1 for j in active if not j.is_recurring)
    return JobList(
        jobs=jobs, recurring_count=recurring, oneoff_count=oneoff,
        recurring_limit=RECURRING_LIMIT, oneoff_limit=ONEOFF_LIMIT,
    )


async def _count_active(db, user_id: str, recurring: bool) -> int:
    clause = ScheduledJob.recurrence.isnot(None) if recurring else ScheduledJob.recurrence.is_(None)
    return (await db.execute(
        select(func.count()).select_from(ScheduledJob)
        .where(ScheduledJob.user_id == user_id, ScheduledJob.status.in_(ACTIVE), clause)
    )).scalar() or 0


async def create_job(user_id: str, jc: JobCreate) -> Job:
    """Create a job, enforcing per-user limits. Raises ValueError if over limit."""
    run_at = jc.run_at if jc.run_at.tzinfo else jc.run_at.replace(tzinfo=timezone.utc)
    async with get_db_session() as db:
        if jc.recurrence and await _count_active(db, user_id, True) >= RECURRING_LIMIT:
            raise ValueError(f"Recurring job limit reached ({RECURRING_LIMIT}). Cancel one first.")
        if not jc.recurrence and await _count_active(db, user_id, False) >= ONEOFF_LIMIT:
            raise ValueError(f"One-off job limit reached ({ONEOFF_LIMIT}). Cancel one first.")
        row = ScheduledJob(
            id=uuid.uuid4().hex[:12], user_id=user_id, name=(jc.name or jc.message[:40]),
            message=jc.message, run_at=run_at, recurrence=jc.recurrence,
            priority=jc.priority, status="pending", chat_id=jc.chat_id,
            context_paths=jc.context_paths or [],
        )
        db.add(row)
        await db.commit()
        await db.refresh(row)
        logger.info(f"Scheduled job {row.id} for {user_id} at {run_at.isoformat()} (recurrence={jc.recurrence})")
        return _to_dto(row)


async def cancel_job(user_id: str, job_id: str) -> bool:
    async with get_db_session() as db:
        row = (await db.execute(
            select(ScheduledJob).where(ScheduledJob.id == job_id, ScheduledJob.user_id == user_id)
        )).scalars().first()
        if not row:
            return False
        row.status = "cancelled"
        await db.commit()
        return True


async def update_job(user_id: str, job_id: str, patch: JobUpdate) -> Optional[Job]:
    async with get_db_session() as db:
        row = (await db.execute(
            select(ScheduledJob).where(ScheduledJob.id == job_id, ScheduledJob.user_id == user_id)
        )).scalars().first()
        if not row:
            return None

        # Determine the resulting recurrence to validate limit changes.
        new_recurrence = row.recurrence
        if patch.clear_recurrence:
            new_recurrence = None
        elif patch.recurrence is not None:
            new_recurrence = patch.recurrence

        # If switching one-off -> recurring, ensure we're under the recurring limit.
        if row.recurrence is None and new_recurrence is not None:
            if await _count_active(db, user_id, True) >= RECURRING_LIMIT:
                raise ValueError(f"Recurring job limit reached ({RECURRING_LIMIT}).")

        if patch.message is not None:
            row.message = patch.message
        if patch.name is not None:
            row.name = patch.name
        if patch.priority is not None:
            row.priority = patch.priority
        if patch.run_at is not None:
            row.run_at = patch.run_at if patch.run_at.tzinfo else patch.run_at.replace(tzinfo=timezone.utc)
        row.recurrence = new_recurrence
        await db.commit()
        await db.refresh(row)
        return _to_dto(row)


# ── scheduling / running ─────────────────────────────────────────────────────

async def reset_stale_running() -> int:
    """On startup, reset jobs stuck in 'running' (crash mid-run) to 'pending'."""
    async with get_db_session() as db:
        result = await db.execute(
            update(ScheduledJob).where(ScheduledJob.status == "running").values(status="pending")
        )
        await db.commit()
        n = result.rowcount or 0
    if n:
        logger.info(f"Reset {n} stale 'running' job(s) to pending")
    return n


async def _claim_due(now: datetime) -> List[Job]:
    """Atomically claim due jobs (mark running) so they never double-run."""
    async with get_db_session() as db:
        rows = (await db.execute(
            select(ScheduledJob)
            .where(ScheduledJob.status == "pending", ScheduledJob.run_at <= now)
            .order_by(ScheduledJob.priority, ScheduledJob.run_at)
            .limit(CLAIM_BATCH)
            .with_for_update(skip_locked=True)
        )).scalars().all()
        claimed = [_to_dto(r) for r in rows]
        for r in rows:
            r.status = "running"
        await db.commit()
    return claimed


async def _finalize(job: Job, *, error: Optional[str]) -> None:
    async with get_db_session() as db:
        row = (await db.execute(
            select(ScheduledJob).where(ScheduledJob.id == job.id)
        )).scalars().first()
        if not row:
            return
        row.last_error = error
        if error is None:
            row.run_count = (row.run_count or 0) + 1
            row.last_run_at = _now()
        if row.recurrence:
            row.run_at = _advance_past_now(row.run_at, row.recurrence)
            row.status = "pending"
        else:
            row.status = "done" if error is None else "failed"
        await db.commit()


async def run_job(job: Job) -> None:
    """Run one claimed job: send its message to the agent (as the user)."""
    try:
        from modules.chat_service import ChatService
        from services.job_auth import get_access_token
        service = ChatService()
        auth_token = await get_access_token(job.user_id)

        chat_id = job.chat_id or f"job-{job.id}"
        message = job.message
        if job.context_paths:
            message += "\n\n[Context files you can read]\n" + "\n".join(job.context_paths[:10])

        async for _ in service.send_message_stream(
            message=message, chat_id=chat_id, user_id=job.user_id,
            auth_token=auth_token,
            page_context={"source": "scheduled_job", "job_id": job.id},
        ):
            pass
        await _finalize(job, error=None)
        logger.info(f"Ran job {job.id}")
    except Exception as e:
        logger.error(f"Job {job.id} failed: {e}")
        await _finalize(job, error=str(e)[:300])


async def run_due_once(now: Optional[datetime] = None) -> int:
    claimed = await _claim_due(now or _now())
    for job in claimed:
        await run_job(job)
    return len(claimed)


async def run_job_loop(interval_seconds: int = 60) -> None:
    """Background waker: recover stale jobs, then run due jobs every interval."""
    logger.info(f"Job scheduler loop started (every {interval_seconds}s)")
    try:
        await reset_stale_running()
    except Exception as e:
        logger.error(f"Stale recovery failed: {e}")
    while True:
        try:
            n = await run_due_once()
            if n:
                logger.info(f"Job scheduler ran {n} due job(s)")
        except Exception as e:
            logger.error(f"Job loop error: {e}")
        await asyncio.sleep(interval_seconds)
