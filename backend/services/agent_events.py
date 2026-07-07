"""Agent activity ledger + "while you were gone" recap.

record_event() is fire-and-forget: it must never break the flow that produced
the event (a job run, an alert, a trade proposal), so it opens its own session
when not given one and swallows failures with a log line.

The recap aggregates events since the user last dismissed it, plus anything
still actionable (pending trade approvals) and forward-looking trust signals
(the agent's next scheduled run) — so the app can open with the agent
accounting for itself instead of generic market data.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db_session
from models.activity import AgentEvent, AgentActivitySeen
from utils.logger import get_logger

logger = get_logger(__name__)

RECAP_MAX_AGE = timedelta(days=7)   # never dig further back than this
RECAP_DEFAULT_WINDOW = timedelta(hours=48)  # first visit / never-dismissed
RECAP_EVENT_LIMIT = 30


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── writing ──────────────────────────────────────────────────────────────────

async def record_event(
    user_id: str,
    event_type: str,
    title: str,
    *,
    body: Optional[str] = None,
    data: Optional[dict] = None,
    value_cents: Optional[int] = None,
    source: Optional[str] = None,
    db: Optional[AsyncSession] = None,
) -> None:
    """Append to the ledger. Never raises."""
    try:
        if db is not None:
            db.add(AgentEvent(
                user_id=user_id, event_type=event_type, source=source,
                title=title[:255], body=body, data=data, value_cents=value_cents,
            ))
            await db.commit()
            return
        async with get_db_session() as session:
            session.add(AgentEvent(
                user_id=user_id, event_type=event_type, source=source,
                title=title[:255], body=body, data=data, value_cents=value_cents,
            ))
            await session.commit()
    except Exception:
        logger.exception("Failed to record agent event %s for %s", event_type, user_id)


# ── reading ──────────────────────────────────────────────────────────────────

def _event_dto(e: AgentEvent) -> dict:
    return {
        "id": str(e.id),
        "event_type": e.event_type,
        "source": e.source,
        "title": e.title,
        "body": e.body,
        "data": e.data or {},
        "value_cents": e.value_cents,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }


async def get_events(
    user_id: str, limit: int = 50, before: Optional[datetime] = None,
    event_type: Optional[str] = None,
) -> list[dict]:
    async with get_db_session() as db:
        q = select(AgentEvent).where(AgentEvent.user_id == user_id)
        if before:
            q = q.where(AgentEvent.created_at < before)
        if event_type:
            q = q.where(AgentEvent.event_type == event_type)
        q = q.order_by(AgentEvent.created_at.desc()).limit(min(limit, 100))
        rows = (await db.execute(q)).scalars().all()
    return [_event_dto(e) for e in rows]


def _headline(counts: dict, pending_count: int, proposed_value_cents: int) -> Optional[str]:
    """Deterministic recap headline. Numbers, not adjectives."""
    bits = []
    runs = counts.get("job_run", 0)
    alerts = counts.get("alert", 0)
    proposed = counts.get("trade_proposed", 0)
    briefs = counts.get("brief", 0)
    insights = counts.get("insight", 0)
    if runs:
        bits.append(f"ran {runs} check{'s' if runs != 1 else ''}")
    if briefs:
        bits.append(f"sent {briefs} brief{'s' if briefs != 1 else ''}")
    if insights:
        bits.append(f"reviewed your holdings")
    if alerts:
        bits.append(f"flagged {alerts} move{'s' if alerts != 1 else ''}")
    if proposed:
        amount = f" (${proposed_value_cents / 100:,.0f})" if proposed_value_cents else ""
        bits.append(f"proposed {proposed} trade{'s' if proposed != 1 else ''}{amount}")
    if not bits and not pending_count:
        return None
    if not bits:
        return "A trade is waiting for your approval."
    if len(bits) == 1:
        summary = bits[0]
    else:
        summary = ", ".join(bits[:-1]) + " and " + bits[-1]
    return f"While you were away, Finch {summary}."


async def _pending_trades(user_id: str) -> list[dict]:
    """Live pending approvals (expires stale ones lazily)."""
    from models.brokerage import PendingTrade
    now = _now()
    out = []
    async with get_db_session() as db:
        rows = (await db.execute(
            select(PendingTrade)
            .where(PendingTrade.user_id == user_id, PendingTrade.status == "pending")
            .order_by(PendingTrade.created_at.desc())
        )).scalars().all()
        for pt in rows:
            if pt.expires_at and now > pt.expires_at:
                pt.status = "expired"
                pt.decided_at = now
                continue
            out.append({
                "id": str(pt.id),
                "summary": pt.summary,
                "order_params": pt.order_params,
                "broker": pt.broker,
                "expires_at": pt.expires_at.isoformat() if pt.expires_at else None,
                "created_at": pt.created_at.isoformat() if pt.created_at else None,
            })
        await db.commit()
    return out


async def _next_scheduled_run(user_id: str) -> Optional[dict]:
    from models.jobs import ScheduledJob
    async with get_db_session() as db:
        row = (await db.execute(
            select(ScheduledJob)
            .where(ScheduledJob.user_id == user_id, ScheduledJob.status == "pending")
            .order_by(ScheduledJob.run_at)
            .limit(1)
        )).scalars().first()
    if not row:
        return None
    return {
        "name": row.name,
        "run_at": row.run_at.isoformat() if row.run_at else None,
        "system_key": row.system_key,
    }


async def _running_now(user_id: str) -> Optional[dict]:
    """The job executing right now, if any — lets the app show the agent
    live-working on home and deep-link into the run chat's stream."""
    from models.jobs import ScheduledJob
    async with get_db_session() as db:
        row = (await db.execute(
            select(ScheduledJob)
            .where(ScheduledJob.user_id == user_id, ScheduledJob.status == "running")
            .order_by(ScheduledJob.run_at.desc())
            .limit(1)
        )).scalars().first()
    if not row:
        return None
    return {
        "name": row.name,
        # run_at ≈ actual start: jobs are claimed (marked running) once due.
        "started_at": row.run_at.isoformat() if row.run_at else None,
        "chat_id": row.chat_id or f"job-{row.id}",
    }


async def get_recap(user_id: str) -> dict:
    now = _now()
    async with get_db_session() as db:
        seen = (await db.execute(
            select(AgentActivitySeen).where(AgentActivitySeen.user_id == user_id)
        )).scalars().first()
        seen_at = seen.seen_at if seen else None

        since = seen_at or (now - RECAP_DEFAULT_WINDOW)
        if since < now - RECAP_MAX_AGE:
            since = now - RECAP_MAX_AGE

        rows = (await db.execute(
            select(AgentEvent)
            .where(AgentEvent.user_id == user_id, AgentEvent.created_at > since)
            .order_by(AgentEvent.created_at.desc())
            .limit(RECAP_EVENT_LIMIT)
        )).scalars().all()

    counts: dict[str, int] = {}
    proposed_value = 0
    for e in rows:
        counts[e.event_type] = counts.get(e.event_type, 0) + 1
        if e.event_type == "trade_proposed" and e.value_cents:
            proposed_value += e.value_cents

    pending = await _pending_trades(user_id)
    next_run = await _next_scheduled_run(user_id)
    running_now = await _running_now(user_id)

    return {
        "since": since.isoformat(),
        "last_seen_at": seen_at.isoformat() if seen_at else None,
        "headline": _headline(counts, len(pending), proposed_value),
        "counts": counts,
        "events": [_event_dto(e) for e in rows],
        "pending_trades": pending,
        "next_run": next_run,
        "running_now": running_now,
        "has_content": bool(rows or pending),
    }


async def mark_seen(user_id: str) -> None:
    async with get_db_session() as db:
        stmt = pg_insert(AgentActivitySeen).values(
            user_id=user_id, seen_at=_now()
        ).on_conflict_do_update(
            index_elements=["user_id"], set_={"seen_at": _now()},
        )
        await db.execute(stmt)
        await db.commit()
