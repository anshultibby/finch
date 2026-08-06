"""
Scheduled job service (Postgres-backed).

A job is a message + planned execution time (+ optional recurrence and context
file paths). The waker claims due jobs with row-locking (FOR UPDATE SKIP LOCKED)
so they never double-run, then runs each by sending its message to the agent —
*as the user* (via a refreshed access token), so authenticated tools work.

Limits per user: RECURRING_LIMIT recurring + ONEOFF_LIMIT one-off active jobs.
Priority is a column (0 = highest); the waker orders due jobs by it.
"""
import re
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
ACTIVE = ("pending", "running", "paused")
CLAIM_BATCH = 25

# System jobs whose runs are NOT comped: the user opted in knowing they spend
# credits (heartbeat settings copy says so explicitly).
UNCOMPED_SYSTEM_KEYS = {"heartbeat", "heartbeat_trigger"}

# Recurring jobs whose runs each get a FRESH chat instead of extending one
# ever-growing thread. Their cross-run memory is the agent-events ledger
# (list_events) + past-chat search — not accumulated chat context.
FRESH_CHAT_SYSTEM_KEYS = {"heartbeat"}

# Credit-spending automations that only run for ACTIVE users (opened the app
# within 72h). Skipped runs just advance the schedule — no credits, no events;
# touch_activity() resumes them the moment the user returns.
ACTIVITY_GATED_SYSTEM_KEYS = {"heartbeat", "heartbeat_trigger"}


def _run_chat_id(row_or_job) -> str:
    """Chat id a run executes in. Fresh-chat jobs get a per-run suffix keyed by
    run_count: retries of a failed run (run_count unchanged) resume that run's
    chat; the next successful cycle moves to a new one."""
    if row_or_job.system_key in FRESH_CHAT_SYSTEM_KEYS:
        return f"job-{row_or_job.id}-r{row_or_job.run_count or 0}"
    return row_or_job.chat_id or f"job-{row_or_job.id}"


def _last_run_chat_id(row) -> str:
    """Chat of the most recent run, for the UI's "view execution" link."""
    if row.system_key in FRESH_CHAT_SYSTEM_KEYS:
        n = row.run_count or 0
        # running or failed → current counter; else last success is n-1.
        if row.status == "running" or row.last_error:
            return f"job-{row.id}-r{n}"
        return f"job-{row.id}-r{max(n - 1, 0)}"
    return row.chat_id or f"job-{row.id}"


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
    # Minute-level interval, e.g. "every_30m" (the heartbeat's format).
    m = re.fullmatch(r"every_(\d+)m", recurrence or "")
    if m:
        return after + timedelta(minutes=max(int(m.group(1)), 5))
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
    # The chat runs execute in (see run_job) — only exposed once a run has
    # started, so the UI doesn't link to a chat that doesn't exist yet.
    has_run = bool(row.run_count or row.last_run_at or row.last_error
                   or row.status == "running")
    return Job(
        id=row.id, user_id=row.user_id, name=row.name, message=row.message,
        run_at=row.run_at, recurrence=row.recurrence, priority=row.priority,
        status=row.status, created_at=row.created_at, last_run_at=row.last_run_at,
        run_count=row.run_count, chat_id=row.chat_id,
        context_paths=row.context_paths or [], last_error=row.last_error,
        last_run_credits=row.last_run_credits or 0, credits_spent=row.credits_spent or 0,
        system_key=row.system_key,
        run_chat_id=_last_run_chat_id(row) if has_run else None,
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
    # System jobs don't consume the user's quota — keep counts consistent
    # with _count_active's limit enforcement.
    recurring = sum(1 for j in active if j.is_recurring and not j.is_system)
    oneoff = sum(1 for j in active if not j.is_recurring and not j.is_system)
    return JobList(
        jobs=jobs, recurring_count=recurring, oneoff_count=oneoff,
        recurring_limit=RECURRING_LIMIT, oneoff_limit=ONEOFF_LIMIT,
    )


async def _count_active(db, user_id: str, recurring: bool) -> int:
    """Active jobs counted against the per-user limits. System jobs are
    Finch-provisioned and don't consume the user's quota."""
    clause = ScheduledJob.recurrence.isnot(None) if recurring else ScheduledJob.recurrence.is_(None)
    return (await db.execute(
        select(func.count()).select_from(ScheduledJob)
        .where(ScheduledJob.user_id == user_id, ScheduledJob.status.in_(ACTIVE),
               ScheduledJob.system_key.is_(None), clause)
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


async def set_status(user_id: str, job_id: str, new_status: str) -> bool:
    async with get_db_session() as db:
        row = (await db.execute(
            select(ScheduledJob).where(ScheduledJob.id == job_id, ScheduledJob.user_id == user_id)
        )).scalars().first()
        if not row:
            return False
        row.status = new_status
        await db.commit()
        return True


async def pause_all(user_id: str) -> int:
    """Pause every pending job for a user. Returns count paused."""
    async with get_db_session() as db:
        result = await db.execute(
            update(ScheduledJob)
            .where(ScheduledJob.user_id == user_id, ScheduledJob.status == "pending")
            .values(status="paused")
        )
        await db.commit()
        return result.rowcount or 0


async def resume_all(user_id: str) -> int:
    async with get_db_session() as db:
        result = await db.execute(
            update(ScheduledJob)
            .where(ScheduledJob.user_id == user_id, ScheduledJob.status == "paused")
            .values(status="pending")
        )
        await db.commit()
        return result.rowcount or 0


async def cancel_job(user_id: str, job_id: str) -> bool:
    async with get_db_session() as db:
        row = (await db.execute(
            select(ScheduledJob).where(ScheduledJob.id == job_id, ScheduledJob.user_id == user_id)
        )).scalars().first()
        if not row:
            return False
        if row.system_key:
            raise ValueError("This is a built-in Finch automation — pause it instead of cancelling.")
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


async def ensure_system_job(user_id: str, system_key: str, name: str, message: str,
                            first_run_at: datetime, recurrence: str = "weekdays",
                            priority: int = 5) -> Job:
    """
    Idempotently provision a Finch built-in automation for a user. If the row
    exists it's left exactly as the user has it (paused stays paused); a
    cancelled/failed row is revived to pending. System jobs don't count against
    limits and their runs are comped (see run_job).
    """
    async with get_db_session() as db:
        row = (await db.execute(
            select(ScheduledJob).where(ScheduledJob.user_id == user_id,
                                       ScheduledJob.system_key == system_key)
        )).scalars().first()
        if row:
            if row.status not in ACTIVE:  # revive a cancelled/done/failed row
                row.status = "pending"
                row.run_at = _advance_past_now(first_run_at, recurrence)
                await db.commit()
                await db.refresh(row)
            return _to_dto(row)
        run_at = first_run_at if first_run_at.tzinfo else first_run_at.replace(tzinfo=timezone.utc)
        if run_at <= _now():
            run_at = _advance_past_now(run_at, recurrence)
        row = ScheduledJob(
            id=uuid.uuid4().hex[:12], user_id=user_id, name=name, message=message,
            run_at=run_at, recurrence=recurrence, priority=priority,
            status="pending", system_key=system_key, context_paths=[],
        )
        db.add(row)
        await db.commit()
        await db.refresh(row)
        logger.info(f"Provisioned system job '{system_key}' for {user_id} (first run {run_at.isoformat()})")
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


async def _user_credits(user_id: str) -> int:
    try:
        from services.credits import CreditsService
        async with get_db_session() as db:
            return await CreditsService.get_user_credits(db, user_id) or 0
    except Exception:
        return 0


async def _finalize(job: Job, *, error: Optional[str], credits: int = 0) -> None:
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
        if credits > 0:
            row.last_run_credits = credits
            row.credits_spent = (row.credits_spent or 0) + credits
        if row.recurrence:
            row.run_at = _advance_past_now(row.run_at, row.recurrence)
            row.status = "pending"
        else:
            row.status = "done" if error is None else "failed"
        await db.commit()


async def _run_outcome_snippet(chat_id: str, max_len: int = 280) -> Optional[str]:
    """First line(s) of the run's final assistant message — what the agent
    concluded, in its own words, for the activity ledger."""
    try:
        from models.chat_models import ChatMessageDB
        async with get_db_session() as db:
            row = (await db.execute(
                select(ChatMessageDB.content)
                .where(ChatMessageDB.chat_id == chat_id, ChatMessageDB.role == "assistant",
                       ChatMessageDB.content != "")
                .order_by(ChatMessageDB.sequence.desc())
                .limit(1)
            )).scalar()
        if not row:
            return None
        text = " ".join(str(row).split())
        return text[:max_len] + ("…" if len(text) > max_len else "")
    except Exception:
        return None


async def _record_run_event(job: Job, chat_id: str, error: Optional[str]) -> None:
    """Ledger entry for the run — including 'looked, nothing needed' runs."""
    try:
        from services.agent_events import record_event
        if error is None:
            snippet = await _run_outcome_snippet(chat_id)
            await record_event(
                job.user_id, "job_run", job.name, body=snippet,
                data={"job_id": job.id, "chat_id": chat_id,
                      "system_key": job.system_key, "status": "ok"},
                source="automation",
            )
        else:
            await record_event(
                job.user_id, "job_run", f"{job.name} — failed", body=error[:300],
                data={"job_id": job.id, "chat_id": chat_id,
                      "system_key": job.system_key, "status": "failed"},
                source="automation",
            )
    except Exception as e:
        logger.warning(f"Failed to record run event for job {job.id}: {e}")


async def _skip_inactive(job: Job) -> None:
    """Advance a claimed job's schedule without running it (user inactive).
    No credits spent, no run recorded — run_count stays put so the next real
    run reuses the pending fresh-chat slot."""
    async with get_db_session() as db:
        row = (await db.execute(
            select(ScheduledJob).where(ScheduledJob.id == job.id)
        )).scalars().first()
        if not row:
            return
        if row.recurrence:
            row.run_at = _advance_past_now(row.run_at, row.recurrence)
            row.status = "pending"
        else:
            row.status = "done"  # one-off tripwire: quietly drop it
        await db.commit()
    logger.info(f"Skipped job {job.id} ({job.name}) — user inactive >72h")


async def run_job(job: Job) -> None:
    """Run one claimed job: send its message to the agent (as the user)."""
    if job.system_key in ACTIVITY_GATED_SYSTEM_KEYS:
        from services.agent_events import is_user_active
        if not await is_user_active(job.user_id):
            await _skip_inactive(job)
            return
    try:
        from modules.chat_service import ChatService
        from services.job_auth import get_access_token
        service = ChatService()
        auth_token = await get_access_token(job.user_id)
        if auth_token is None:
            logger.error(
                f"Job {job.id} ({job.name}) for {job.user_id}: no auth token — "
                "running with public tools only. If this persists the user's "
                "refresh token is revoked and they must sign in again."
            )

        chat_id = _run_chat_id(job)
        message = job.message
        if job.context_paths:
            message += "\n\n[Context files you can read]\n" + "\n".join(job.context_paths[:10])

        before = await _user_credits(job.user_id)
        async for _ in service.send_message_stream(
            message=message, chat_id=chat_id, user_id=job.user_id,
            auth_token=auth_token,
            page_context={"source": "scheduled_job", "job_id": job.id},
        ):
            pass
        after = await _user_credits(job.user_id)
        spent = max(0, before - after)
        if job.system_key and job.system_key not in UNCOMPED_SYSTEM_KEYS and spent > 0:
            # System automations are on the house: refund what the run consumed.
            from services.credits import CreditsService
            async with get_db_session() as db:
                await CreditsService.add_credits(
                    db, job.user_id, spent,
                    transaction_type="system_job_comp",
                    description=f"Built-in automation '{job.name}' — run comped",
                    metadata={"job_id": job.id, "system_key": job.system_key},
                )
            logger.info(f"Comped {spent} credits for system job {job.id}")
            spent = 0
        await _finalize(job, error=None, credits=spent)
        await _record_run_event(job, chat_id, error=None)
        logger.info(f"Ran job {job.id} (spent {spent} credits)")
    except Exception as e:
        logger.error(f"Job {job.id} failed: {e}")
        await _finalize(job, error=str(e)[:300])
        await _record_run_event(job, _run_chat_id(job), error=str(e)[:300])


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
