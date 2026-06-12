"""
Finch built-in automations — definitions + provisioning.

A system job is a ScheduledJob with a system_key: provisioned by Finch when it
becomes relevant (not at signup — a job that has nothing to do just burns
tokens), exempt from the per-user recurring limit, comped (runs refund their
credits), pausable in the Automations panel but not cancellable.

Currently: the nightly day-trading PLAN heartbeat, provisioned when the user
connects a Robinhood agentic account.
"""
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

# 22:00 UTC = 18:00 ET in summer / 17:00 ET in winter — always after the close,
# and still the same UTC calendar day, so the "weekdays" recurrence (which
# advances on UTC dates) matches US trading weekdays. Do NOT move this into the
# ET evening past 20:00 — that crosses UTC midnight and Friday's run would land
# on a UTC Saturday and get skipped to Monday.
_NIGHTLY_UTC = time(22, 0)

_NIGHTLY_MESSAGE = (
    "Nightly day-trading PLAN run (built-in automation — the user can pause this "
    "in Automations). Read the day_trading skill and execute its PLAN decision "
    "point exactly: session() guard (skip if today wasn't a trading day), "
    "session_state(), reconcile journal vs broker, grade today's trades, apply "
    "kill criteria via setup_stats(), pull tomorrow's earnings calendar (FMP) and "
    "macro events (fred skill), set tomorrow's risk and rules of engagement, "
    "write_plan(), append_note(). Then ensure the next trading day's intraday "
    "decision-point jobs exist — one-off ENTRY/MANAGE/FLATTEN per the skill's "
    "Scheduling section (list_jobs() first; create only what's missing). Place "
    "no orders. If the operation isn't set up (no strategy and no journal), keep "
    "it to a one-paragraph plan, schedule nothing, and stop — stay cheap."
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
