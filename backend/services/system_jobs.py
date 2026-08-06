"""
Finch built-in automations — definitions + provisioning.

A system job is a ScheduledJob with a system_key: provisioned by Finch when it
becomes relevant (not at signup — a job that has nothing to do just burns
tokens), exempt from the per-user recurring limit, comped (runs refund their
credits), pausable in the Automations panel but not cancellable.

Currently: the nightly day-trading PLAN heartbeat, provisioned when the user
connects a Robinhood agentic account.
"""
import uuid
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select

from core.database import get_db_session
from models.jobs import ScheduledJob
from services.job_scheduler import ensure_system_job
from utils.logger import get_logger

logger = get_logger(__name__)

DAY_TRADING_NIGHTLY = "day_trading_nightly"
MORNING_BRIEF = "morning_brief"
HEARTBEAT = "heartbeat"
HEARTBEAT_TRIGGER = "heartbeat_trigger"  # one-off runs the market monitor fires

# 22:00 UTC = 18:00 ET in summer / 17:00 ET in winter — always after the close,
# and still the same UTC calendar day, so the "weekdays" recurrence (which
# advances on UTC dates) matches US trading weekdays. Do NOT move this into the
# ET evening past 20:00 — that crosses UTC midnight and Friday's run would land
# on a UTC Saturday and get skipped to Monday.
_NIGHTLY_UTC = time(22, 0)

_NIGHTLY_MESSAGE = (
    "You are this account's autonomous day-trading agent (built-in automation — "
    "the user can pause it in Automations). GOAL: grow the account by "
    "day-trading, trading LIVE — place real orders, no paper ramp. You are "
    "authorized to place orders DIRECTLY and unattended within the code risk "
    "gates (no email approval — the risk gates are the safety, not a human "
    "click). You wake at scheduled triggers, act toward the goal, and schedule "
    "your own next wakeup; this nightly trigger is your anchor — after the close, "
    "review and set up the next session.\n"
    "This run: read the day_trading skill's SKILL.md for the tools available to "
    "you (clock/session, stocks_in_play, orb_signal & the other setups, "
    "RiskBudget + plan_trade risk gates, robinhood execution, journal). Use them "
    "as you judge best — they're tools, not a fixed script. session() guard (stop "
    "if today wasn't a trading day); reconcile journal vs broker; grade today's "
    "closed trades; update strategy.md (and delete any leftover paper-ramp / "
    "go-live policy — the owner removed the ramp, you trade live now); build the "
    "next session's watch list + event map (FMP earnings, fred macro); "
    "write_plan(); append_note(). Place no orders now — the market is closed.\n"
    "Then SCHEDULE your next wakeup with schedule_job(): the next session's first "
    "trading wake at 09:36 ET, plus a mandatory FLATTEN wake near the close as a "
    "safety net (convert each ET time to UTC for that DATE via the clock helpers, "
    "never a remembered offset). Give each wake a plain goal in its message "
    "('trade the open toward the goal, within the hard risk limits, then schedule "
    "your next manage/flatten wake'). Every wake reconciles first and stays "
    "inside the code risk gates (1%/trade, −3% day stop, 3-loss stop, ≤10 "
    "trades/day, longs only); each schedules the next wake it needs, self-chaining "
    "until FLATTEN. If the operation isn't set up yet (no strategy, no journal), "
    "bootstrap a one-paragraph plan, schedule tomorrow's first wake, and stop."
)


def _next_nightly_utc() -> datetime:
    now = datetime.now(timezone.utc)
    run = now.replace(hour=_NIGHTLY_UTC.hour, minute=_NIGHTLY_UTC.minute,
                      second=0, microsecond=0)
    if run <= now:
        run += timedelta(days=1)
    while run.weekday() >= 5:
        run += timedelta(days=1)
    return run


_BRIEF_MESSAGE = (
    "Morning brief run (built-in automation — the user can pause this in "
    "Automations). Compose the user's daily pre-market brief:\n"
    "1) Call get_portfolio for holdings (skip silently if no brokerage is "
    "connected) and fetch the user's watchlist.\n"
    "2) For the union of those symbols: overnight/latest price moves, notable "
    "news since yesterday (use indian_stocks for NSE/BSE symbols), and any "
    "earnings or dividends in the next 7 days. Add at most 2 macro events that "
    "actually matter today.\n"
    "3) Write a tight markdown brief — sections: 'Your stocks' (biggest movers "
    "with the one-line why), 'News that matters' (3-5 items, one line each), "
    "'Coming up' (dates). End with a single insight worth acting on. Under 350 "
    "words, no fluff, no preamble.\n"
    "4) Deliver it: in the sandbox, `from skills.finch_api.scripts import "
    "send_morning_brief` and call send_morning_brief(subject, markdown). "
    "Subject format: 'Finch brief: <top mover or theme>'.\n"
    "If the user has neither holdings nor a watchlist, send a 100-word market "
    "overview (major indices, the one story of the day) and suggest adding "
    "stocks to their watchlist for a personalized brief. Stay cheap: no deep "
    "research, no visualizations."
)


def _next_brief_utc(time_str: str, tz_name: str) -> datetime:
    """Next occurrence of the user's local brief time, as UTC.

    The 'daily' recurrence then advances in fixed UTC steps, so DST-observing
    zones drift by an hour between season changes until the user re-saves their
    settings. Acceptable for a brief; IST (no DST) is unaffected.
    """
    tz = ZoneInfo(tz_name)
    hour, minute = (int(p) for p in time_str.split(":")[:2])
    now_local = datetime.now(tz)
    run_local = now_local.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if run_local <= now_local:
        run_local += timedelta(days=1)
    return run_local.astimezone(timezone.utc)


async def configure_morning_brief(
    user_id: str, enabled: bool, time_str: str, tz_name: str
) -> None:
    """Provision, retime, or pause the user's daily morning brief.

    Raises ValueError on a bad time/timezone so the caller can reject the save.
    """
    try:
        run_at = _next_brief_utc(time_str or "08:00", tz_name or "UTC")
    except Exception:
        raise ValueError(f"Invalid brief time/timezone: {time_str!r} / {tz_name!r}")

    if enabled:
        await ensure_system_job(
            user_id=user_id,
            system_key=MORNING_BRIEF,
            name="Morning brief",
            message=_BRIEF_MESSAGE,
            first_run_at=run_at,
            recurrence="daily",
        )

    # ensure_system_job leaves an existing row untouched, so apply the (possibly
    # changed) schedule and enabled state directly. Also refresh the message so
    # prompt improvements reach existing jobs.
    async with get_db_session() as db:
        row = (await db.execute(
            select(ScheduledJob).where(ScheduledJob.user_id == user_id,
                                       ScheduledJob.system_key == MORNING_BRIEF)
        )).scalars().first()
        if not row:
            return  # disabled and never provisioned
        if row.status != "running":
            row.status = "pending" if enabled else "paused"
        if enabled:
            row.run_at = run_at
            row.message = _BRIEF_MESSAGE
        await db.commit()
    logger.info(
        f"Morning brief for {user_id}: enabled={enabled} "
        f"time={time_str} tz={tz_name} next_run={run_at.isoformat()}"
    )


# ── heartbeat: the passive analyst in your pocket ────────────────────────────
# A recurring agentic run that watches the user's portfolio, watchlist and
# news; writes what it finds into the activity ledger (report_insight) and is
# the single source of alerts for heartbeat users. Unlike other system jobs it
# is NOT comped — the user opts in knowing it spends credits (Settings copy).
# Interval is minute-level for Pro; free users are fixed to daily (gated in
# routes/account.py).

HEARTBEAT_MIN_INTERVAL_MINUTES = 5
HEARTBEAT_DAILY_MINUTES = 24 * 60

_HEARTBEAT_MESSAGE = (
    "Heartbeat run (built-in automation — this spends the user's credits; they "
    "can pause it or change how often it runs in Settings). You are the user's "
    "passive analyst: check their portfolio, watchlist, and news for those "
    "symbols. Each run is a FRESH chat — your memory lives in the ledger: "
    "`from skills.finch_api.scripts import list_events, search_past_chats, "
    "report_insight`. Start with list_events(limit=15) to see what you already "
    "reported and never repeat it; use search_past_chats('NVDA thesis') if you "
    "need deeper context from earlier runs or the user's own conversations. "
    "When something a holder should know about has changed, "
    "report_insight(title, body, alert=False) — alert=True only when it's "
    "urgent enough to interrupt their day. If nothing meaningful changed, "
    "reply with one short line saying so. Stay cheap and be judicious about "
    "what's worth the user's attention."
)


async def configure_heartbeat(user_id: str, enabled: bool, interval_minutes: int) -> None:
    """Provision, re-time, or pause the user's heartbeat."""
    interval = max(int(interval_minutes), HEARTBEAT_MIN_INTERVAL_MINUTES)
    recurrence = f"every_{interval}m"
    # First run lands ~2 minutes out so enabling feels immediately alive.
    first_run = datetime.now(timezone.utc) + timedelta(minutes=2)

    if enabled:
        await ensure_system_job(
            user_id=user_id,
            system_key=HEARTBEAT,
            name="Heartbeat — portfolio & news watch",
            message=_HEARTBEAT_MESSAGE,
            first_run_at=first_run,
            recurrence=recurrence,
        )

    # ensure_system_job leaves an existing row untouched — apply the (possibly
    # changed) interval and enabled state directly, and refresh the message so
    # prompt improvements reach existing jobs.
    async with get_db_session() as db:
        row = (await db.execute(
            select(ScheduledJob).where(ScheduledJob.user_id == user_id,
                                       ScheduledJob.system_key == HEARTBEAT)
        )).scalars().first()
        if not row:
            return  # disabled and never provisioned
        if row.status != "running":
            row.status = "pending" if enabled else "paused"
        if enabled:
            row.recurrence = recurrence
            row.message = _HEARTBEAT_MESSAGE
            row.run_at = first_run
        await db.commit()
    logger.info(f"Heartbeat for {user_id}: enabled={enabled} every {interval}m")


async def trigger_heartbeat_now(user_id: str, reason: str) -> bool:
    """Fire a one-off heartbeat run immediately (the market-monitor tripwire).
    Skips if a trigger is already pending/running so a volatile day can't
    stack investigations, and for users inactive >72h (the recurring heartbeat
    is likewise gated — it resumes when they return). Returns True if a run
    was enqueued."""
    from services.agent_events import is_user_active
    if not await is_user_active(user_id):
        return False
    now = datetime.now(timezone.utc)
    async with get_db_session() as db:
        existing = (await db.execute(
            select(ScheduledJob).where(
                ScheduledJob.user_id == user_id,
                ScheduledJob.system_key == HEARTBEAT_TRIGGER,
                ScheduledJob.status.in_(("pending", "running")),
            )
        )).scalars().first()
        if existing:
            return False
        db.add(ScheduledJob(
            id=uuid.uuid4().hex[:12], user_id=user_id,
            name="Heartbeat — market tripwire",
            message=(
                f"Market tripwire (auto-triggered heartbeat run — spends the "
                f"user's credits): {reason}. Check list_events() from "
                "skills.finch_api.scripts first so you don't re-report, then "
                "investigate why, judge what it means for the user's "
                "portfolio/watchlist, and report_insight(title, body, alert=...) "
                "— alert=True only if a holder should know right now. Stay cheap."
            ),
            run_at=now, recurrence=None, priority=3,
            status="pending", system_key=HEARTBEAT_TRIGGER, context_paths=[],
        ))
        await db.commit()
    logger.info(f"Heartbeat tripwire enqueued for {user_id}: {reason}")
    return True


async def ensure_day_trading_nightly(user_id: str) -> None:
    """Provision (or revive) the nightly PLAN heartbeat. Safe to call on every
    Robinhood connect — it's idempotent and respects a user's pause."""
    try:
        await ensure_system_job(
            user_id=user_id,
            system_key=DAY_TRADING_NIGHTLY,
            name="Nightly trading plan",
            message=_NIGHTLY_MESSAGE,
            first_run_at=_next_nightly_utc(),
            recurrence="weekdays",
        )
        # ensure_system_job leaves existing rows untouched — refresh the message
        # so prompt improvements reach already-provisioned jobs.
        async with get_db_session() as db:
            row = (await db.execute(
                select(ScheduledJob).where(ScheduledJob.user_id == user_id,
                                           ScheduledJob.system_key == DAY_TRADING_NIGHTLY)
            )).scalars().first()
            if row and row.message != _NIGHTLY_MESSAGE:
                row.message = _NIGHTLY_MESSAGE
                await db.commit()
    except Exception as e:
        # Provisioning must never break the connect flow.
        logger.error(f"Failed to provision {DAY_TRADING_NIGHTLY} for {user_id}: {e}")
