"""
Scheduled job service (Postgres-backed).

An automation is a time + an instruction. Either the user or the agent creates
one; the waker claims due rows (FOR UPDATE SKIP LOCKED, so they never
double-run) and runs each instruction as the user, via a backend-minted session
so authenticated tools work.

Every run executes in a FRESH chat. Cross-run memory is the agent-events ledger
(list_events) and past-chat search — not an ever-growing thread.

Two behaviours vary per job and are columns on the row, not special cases here:
  comped          — the run's credits are refunded (Finch-provided built-ins)
  activity_gated  — skip the run if the user hasn't opened the app in 72h

Limits per user: RECURRING_LIMIT recurring + ONEOFF_LIMIT one-off active jobs.
Built-ins (system_key set) don't count against either.
"""
import re
import uuid
import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from sqlalchemy import select, func, update

from core.database import get_db_session
from models.jobs import ScheduledJob, JOB_CHAT_PREFIX
from schemas.jobs import Job, JobCreate, JobUpdate, JobList
from utils.logger import get_logger

logger = get_logger(__name__)

RECURRING_LIMIT = 5
ONEOFF_LIMIT = 10
ACTIVE = ("pending", "running", "paused")
CLAIM_BATCH = 25


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _run_chat_id(job_id: str, run_count: int) -> str:
    """Chat a run executes in. Keyed by run_count so a retry of a failed run
    (run_count unchanged) resumes that run's chat, while the next successful
    cycle moves to a new one."""
    return f"{JOB_CHAT_PREFIX}{job_id}-r{run_count or 0}"


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
    # Only expose the run chat once a run has started, so the UI doesn't link
    # to a chat that doesn't exist yet.
    n = row.run_count or 0
    has_run = bool(n or row.last_run_at or row.last_error or row.status == "running")
    # Mid-run or after a failure the current counter is the live chat;
    # otherwise the last success was the previous one.
    current = row.status == "running" or bool(row.last_error)
    return Job(
        id=row.id, user_id=row.user_id, name=row.name, message=row.message,
        run_at=row.run_at, recurrence=row.recurrence, status=row.status,
        created_at=row.created_at, last_run_at=row.last_run_at, run_count=n,
        last_error=row.last_error, last_run_credits=row.last_run_credits or 0,
        credits_spent=row.credits_spent or 0, system_key=row.system_key,
        comped=bool(row.comped), activity_gated=bool(row.activity_gated),
        run_chat_id=_run_chat_id(row.id, n if current else max(n - 1, 0)) if has_run else None,
    )


# ── CRUD ─────────────────────────────────────────────────────────────────────

async def list_jobs(user_id: str) -> JobList:
    async with get_db_session() as db:
        rows = (await db.execute(
            select(ScheduledJob).where(ScheduledJob.user_id == user_id)
            .order_by(ScheduledJob.run_at)
        )).scalars().all()
    jobs = [_to_dto(r) for r in rows]
    active = [j for j in jobs if j.status in ACTIVE]
    # Built-ins don't consume the user's quota — keep counts consistent with
    # _count_active's limit enforcement.
    recurring = sum(1 for j in active if j.is_recurring and not j.is_system)
    oneoff = sum(1 for j in active if not j.is_recurring and not j.is_system)
    return JobList(
        jobs=jobs, recurring_count=recurring, oneoff_count=oneoff,
        recurring_limit=RECURRING_LIMIT, oneoff_limit=ONEOFF_LIMIT,
    )


async def _count_active(db, user_id: str, recurring: bool) -> int:
    """Active jobs counted against the per-user limits. Built-ins are
    Finch-provisioned and don't consume the user's quota."""
    clause = ScheduledJob.recurrence.isnot(None) if recurring else ScheduledJob.recurrence.is_(None)
    return (await db.execute(
        select(func.count()).select_from(ScheduledJob)
        .where(ScheduledJob.user_id == user_id, ScheduledJob.status.in_(ACTIVE),
               ScheduledJob.system_key.is_(None), clause)
    )).scalar() or 0


async def schedule(
    user_id: str,
    *,
    message: str,
    run_at: datetime,
    name: Optional[str] = None,
    recurrence: Optional[str] = None,
    key: Optional[str] = None,
    comped: bool = False,
    activity_gated: bool = False,
    enforce_limits: bool = True,
) -> Job:
    """Create or update one automation — the single write path.

    Without `key` this always creates a new row (an ordinary user/agent job,
    subject to the per-user limits).

    With `key` it's an idempotent upsert of a Finch built-in: one row per
    (user, key). An existing row keeps the user's own status — a paused brief
    stays paused — but its instruction, cadence and next run time are refreshed,
    so prompt and schedule changes reach already-provisioned jobs. A row the
    user cancelled, or one that finished/failed, is revived to pending.

    Raises ValueError if a limit-enforced create would exceed the user's quota.
    """
    run_at = _utc(run_at)
    async with get_db_session() as db:
        row = None
        if key:
            row = (await db.execute(
                select(ScheduledJob).where(ScheduledJob.user_id == user_id,
                                           ScheduledJob.system_key == key)
            )).scalars().first()

        if row is None:
            if enforce_limits:
                if recurrence and await _count_active(db, user_id, True) >= RECURRING_LIMIT:
                    raise ValueError(f"Recurring job limit reached ({RECURRING_LIMIT}). Cancel one first.")
                if not recurrence and await _count_active(db, user_id, False) >= ONEOFF_LIMIT:
                    raise ValueError(f"One-off job limit reached ({ONEOFF_LIMIT}). Cancel one first.")
            if key and recurrence and run_at <= _now():
                run_at = _advance_past_now(run_at, recurrence)
            row = ScheduledJob(
                id=uuid.uuid4().hex[:12], user_id=user_id,
                name=(name or message[:40]), message=message, run_at=run_at,
                recurrence=recurrence, status="pending", system_key=key,
                comped=comped, activity_gated=activity_gated,
            )
            db.add(row)
        else:
            row.message = message
            row.recurrence = recurrence
            row.comped = comped
            row.activity_gated = activity_gated
            if name:
                row.name = name
            # Don't yank a run that's in flight out from under itself.
            if row.status != "running":
                row.run_at = run_at
                if row.status not in ACTIVE:  # revive cancelled/done/failed
                    row.status = "pending"

        await db.commit()
        await db.refresh(row)
        logger.info(
            f"Scheduled '{row.name}' ({row.id}) for {user_id} at "
            f"{row.run_at.isoformat()} (recurrence={recurrence}, key={key})"
        )
        return _to_dto(row)


async def create_job(user_id: str, jc: JobCreate) -> Job:
    """Create a user- or agent-scheduled automation. Raises ValueError if over limit."""
    return await schedule(
        user_id, message=jc.message, run_at=jc.run_at,
        name=jc.name, recurrence=jc.recurrence,
    )


async def set_enabled(user_id: str, key: str, enabled: bool) -> bool:
    """Pause/resume a built-in by key. No-op if it was never provisioned."""
    async with get_db_session() as db:
        row = (await db.execute(
            select(ScheduledJob).where(ScheduledJob.user_id == user_id,
                                       ScheduledJob.system_key == key)
        )).scalars().first()
        if not row:
            return False
        if row.status != "running":
            row.status = "pending" if enabled else "paused"
        await db.commit()
        return True


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

        new_recurrence = row.recurrence
        if patch.clear_recurrence:
            new_recurrence = None
        elif patch.recurrence is not None:
            new_recurrence = patch.recurrence

        # Switching one-off -> recurring must respect the recurring limit.
        if row.recurrence is None and new_recurrence is not None:
            if await _count_active(db, user_id, True) >= RECURRING_LIMIT:
                raise ValueError(f"Recurring job limit reached ({RECURRING_LIMIT}).")

        if patch.message is not None:
            row.message = patch.message
        if patch.name is not None:
            row.name = patch.name
        if patch.run_at is not None:
            row.run_at = _utc(patch.run_at)
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
            .order_by(ScheduledJob.run_at)
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
        data = {"job_id": job.id, "chat_id": chat_id, "system_key": job.system_key}
        if error is None:
            await record_event(
                job.user_id, "job_run", job.name,
                body=await _run_outcome_snippet(chat_id),
                data={**data, "status": "ok"}, source="automation",
            )
        else:
            await record_event(
                job.user_id, "job_run", f"{job.name} — failed", body=error[:300],
                data={**data, "status": "failed"}, source="automation",
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
    """Run one claimed job: send its instruction to the agent, as the user."""
    if job.activity_gated:
        from services.agent_events import is_user_active
        if not await is_user_active(job.user_id):
            await _skip_inactive(job)
            return

    chat_id = _run_chat_id(job.id, job.run_count)
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

        before = await _user_credits(job.user_id)
        async for _ in service.send_message_stream(
            message=job.message, chat_id=chat_id, user_id=job.user_id,
            auth_token=auth_token,
            page_context={"source": "scheduled_job", "job_id": job.id},
        ):
            pass
        spent = max(0, before - await _user_credits(job.user_id))

        if job.comped and spent > 0:
            # Finch-provided automation: refund what the run consumed.
            from services.credits import CreditsService
            async with get_db_session() as db:
                await CreditsService.add_credits(
                    db, job.user_id, spent,
                    transaction_type="system_job_comp",
                    description=f"Built-in automation '{job.name}' — run comped",
                    metadata={"job_id": job.id, "system_key": job.system_key},
                )
            logger.info(f"Comped {spent} credits for job {job.id}")
            spent = 0

        await _finalize(job, error=None, credits=spent)
        await _record_run_event(job, chat_id, error=None)
        logger.info(f"Ran job {job.id} (spent {spent} credits)")
    except Exception as e:
        logger.error(f"Job {job.id} failed: {e}")
        await _finalize(job, error=str(e)[:300])
        await _record_run_event(job, chat_id, error=str(e)[:300])


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
