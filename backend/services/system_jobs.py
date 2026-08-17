"""
Finch built-in automations.

A built-in is an ordinary automation (a time + an instruction) that Finch
provisions on the user's behalf and identifies by `system_key`. The only things
that make it special: it's exempt from the per-user limits, and it's pausable
rather than cancellable. Two per-job behaviours — whether runs are comped and
whether they pause for inactive users — are columns, declared here.

Provisioning is one call: job_scheduler.schedule(..., key=...). It upserts, so
editing an instruction below reaches already-provisioned jobs on the next
provision, while respecting a user's pause.

Built-ins are provisioned when they become relevant (not at signup — a job with
nothing to do just burns tokens).
"""
import uuid
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select

from core.database import get_db_session
from models.jobs import ScheduledJob
from services.job_scheduler import schedule, set_enabled
from utils.logger import get_logger

logger = get_logger(__name__)

DAY_TRADING_NIGHTLY = "day_trading_nightly"
MORNING_BRIEF = "morning_brief"
HEARTBEAT = "heartbeat"
HEARTBEAT_TRIGGER = "heartbeat_trigger"  # one-off runs the market monitor fires
CATALYST_IDEAS = "catalyst_ideas"


# ── nightly day-trading plan ─────────────────────────────────────────────────
# 22:00 UTC = 18:00 ET in summer / 17:00 ET in winter — always after the close,
# and still the same UTC calendar day, so the "weekdays" recurrence (which
# advances on UTC dates) matches US trading weekdays. Do NOT move this into the
# ET evening past 20:00 — that crosses UTC midnight and Friday's run would land
# on a UTC Saturday and get skipped to Monday.
_NIGHTLY_UTC = time(22, 0)

_NIGHTLY_MESSAGE = (
    "Nightly trading review (built-in automation — the user can pause it in "
    "Automations).\n"
    "You are this account's autonomous day-trading agent. GOAL: grow the account "
    "by day-trading LIVE and unattended — place real orders directly, no email "
    "approval, no paper ramp. There are NO risk limits; size and pace entirely "
    "as you judge best. Longs only (broker constraint, not ours).\n"
    "Read `skills/day_trading/SKILL.md` and follow its 'Nightly review' section. "
    "That file is the recipe and the thing kept current — this message only sets "
    "the goal and the mandate.\n"
    "Open with `journal.session_state()`; treat it as your only memory read "
    "unless it leaves something specific missing. Place no orders — the market "
    "is closed.\n"
    "Close the run the way the skill says: schedule the next session's wakeups, "
    "then `append_note(did, next_steps=...)`. Each run is a FRESH chat, and "
    "`next_steps` is the first thing the next run sees — put the real handoff "
    "there. If the operation isn't set up yet (no strategy.md, no journal), "
    "bootstrap a one-paragraph plan, schedule tomorrow's first wakeup, and stop."
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


async def ensure_day_trading_nightly(user_id: str) -> None:
    """Provision (or refresh) the nightly review wakeup. Safe to call on every
    Robinhood connect — idempotent and pause-respecting."""
    try:
        await schedule(
            user_id, key=DAY_TRADING_NIGHTLY, name="Nightly trading plan",
            message=_NIGHTLY_MESSAGE, run_at=_next_nightly_utc(),
            recurrence="weekdays", comped=True, enforce_limits=False,
        )
    except Exception as e:
        # Provisioning must never break the connect flow.
        logger.error(f"Failed to provision {DAY_TRADING_NIGHTLY} for {user_id}: {e}")


# ── morning brief ────────────────────────────────────────────────────────────

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
        await schedule(
            user_id, key=MORNING_BRIEF, name="Morning brief",
            message=_BRIEF_MESSAGE, run_at=run_at, recurrence="daily",
            comped=True, enforce_limits=False,
        )
    await set_enabled(user_id, MORNING_BRIEF, enabled)
    logger.info(
        f"Morning brief for {user_id}: enabled={enabled} "
        f"time={time_str} tz={tz_name} next_run={run_at.isoformat()}"
    )


# ── catalyst ideas ───────────────────────────────────────────────────────────
# Just a wakeup and an instruction. Everything it needs — the scanners, the
# registry, the scorecard — lives in the catalyst_ideas skill, so improving the
# bot means editing the skill, not this file.

# 13:00 UTC = 09:00 ET summer / 08:00 ET winter: after the pre-market reaction
# to last night's after-close reporters, before the open. Same-UTC-day as the
# session, so the weekdays recurrence lines up with trading days.
_IDEAS_UTC = time(13, 0)

_IDEAS_MESSAGE = (
    "Catalyst idea run (built-in automation — the user can pause it in "
    "Automations). Read the catalyst_ideas SKILL.md and follow it.\n"
    "Goal: surface the few short-term, catalyst-driven trade ideas genuinely "
    "worth this user's attention today, and be honest about how your past ones "
    "did.\n"
    "Start with `list_ideas()` and its by_catalyst scorecard — lean into the "
    "catalyst types actually earning alpha here, stop proposing the ones that "
    "aren't. Two or three ideas you'd defend beat ten weak ones; everything you "
    "propose is graded whether or not the user acts on it.\n"
    "Nothing clearing the bar is a real answer — say so in one line and stop. "
    "Pull detail only for the names you're seriously considering; a scan result "
    "is a shortlist, not something to read end to end."
)


def _next_ideas_utc() -> datetime:
    now = datetime.now(timezone.utc)
    run = now.replace(hour=_IDEAS_UTC.hour, minute=_IDEAS_UTC.minute,
                      second=0, microsecond=0)
    if run <= now:
        run += timedelta(days=1)
    while run.weekday() >= 5:
        run += timedelta(days=1)
    return run


async def configure_catalyst_ideas(user_id: str, enabled: bool = True) -> None:
    """Provision, refresh, or pause the daily catalyst-idea run."""
    if enabled:
        await schedule(
            user_id, key=CATALYST_IDEAS, name="Catalyst ideas — daily scan",
            message=_IDEAS_MESSAGE, run_at=_next_ideas_utc(),
            recurrence="weekdays", activity_gated=True, enforce_limits=False,
        )
    await set_enabled(user_id, CATALYST_IDEAS, enabled)
    logger.info(f"Catalyst ideas for {user_id}: enabled={enabled}")


# ── heartbeat: the passive analyst in your pocket ────────────────────────────
# A recurring agentic run that watches the user's portfolio, watchlist and news
# and writes what it finds into the activity ledger (report_insight). Unlike the
# other built-ins it is NOT comped — the user opts in knowing it spends credits
# (Settings copy says so) — and it IS activity-gated, so it stops burning
# credits for users who've stopped opening the app. Interval is minute-level for
# Pro; free users are fixed to daily (gated in routes/account.py).

HEARTBEAT_MIN_INTERVAL_MINUTES = 5
HEARTBEAT_DAILY_MINUTES = 24 * 60

_HEARTBEAT_MESSAGE = (
    "Heartbeat run (built-in automation — this spends the user's credits; they "
    "can pause it or change how often it runs in Settings). You are the user's "
    "passive analyst: check their portfolio, watchlist, and news for those "
    "symbols.\n"
    "`from skills.finch_api.scripts import list_events, search_past_chats, "
    "report_insight`. Each run is a FRESH chat and the ledger is your memory: "
    "open with `list_events(limit=15)` so you never re-report something, and "
    "reach for `search_past_chats('NVDA thesis')` only when a specific name "
    "needs history you don't have.\n"
    "Work outward-in: start from the quote-level view of the whole book, and "
    "pull news or detail ONLY for the two or three names that actually moved. "
    "Reading everything about everything is the failure mode here — most runs "
    "should touch very little.\n"
    "When something a holder should know has changed, `report_insight(title, "
    "body, alert=False)`; alert=True only when it's urgent enough to interrupt "
    "their day. If nothing meaningful changed, reply with one short line saying "
    "so — that's the expected outcome most of the time, and it should be cheap."
)


async def configure_heartbeat(user_id: str, enabled: bool, interval_minutes: int) -> None:
    """Provision, re-time, or pause the user's heartbeat."""
    interval = max(int(interval_minutes), HEARTBEAT_MIN_INTERVAL_MINUTES)
    if enabled:
        await schedule(
            user_id, key=HEARTBEAT, name="Heartbeat — portfolio & news watch",
            message=_HEARTBEAT_MESSAGE,
            # First run lands ~2 minutes out so enabling feels immediately alive.
            run_at=datetime.now(timezone.utc) + timedelta(minutes=2),
            recurrence=f"every_{interval}m",
            activity_gated=True, enforce_limits=False,
        )
    await set_enabled(user_id, HEARTBEAT, enabled)
    logger.info(f"Heartbeat for {user_id}: enabled={enabled} every {interval}m")


# ── keeping provisioned rows in step with the text above ─────────────────────

async def refresh_builtin_messages() -> int:
    """Push edits to the instructions above onto already-provisioned rows.

    Built-ins are otherwise only re-provisioned when their trigger fires again
    (a Robinhood connect, a settings save), so a user who connected months ago
    keeps running whatever text shipped that day. That's fine for wording, and
    not fine for the things these messages control — cost, scope, mandate.

    Only `message` is touched: status, run_at, cadence and the user's pause all
    survive. Idempotent, so it's safe on every boot.
    """
    updates = {
        DAY_TRADING_NIGHTLY: _NIGHTLY_MESSAGE,
        MORNING_BRIEF: _BRIEF_MESSAGE,
        CATALYST_IDEAS: _IDEAS_MESSAGE,
        HEARTBEAT: _HEARTBEAT_MESSAGE,
    }
    changed = 0
    try:
        async with get_db_session() as db:
            for key, message in updates.items():
                rows = (await db.execute(
                    select(ScheduledJob).where(
                        ScheduledJob.system_key == key,
                        ScheduledJob.message != message,
                    )
                )).scalars().all()
                for row in rows:
                    row.message = message
                    changed += 1
            await db.commit()
    except Exception as e:
        # A refresh failure must never block startup — the old text still runs.
        logger.error(f"Built-in message refresh failed: {e}")
        return 0
    if changed:
        logger.info(f"Refreshed {changed} built-in automation instruction(s)")
    return changed


async def trigger_heartbeat_now(user_id: str, reason: str) -> bool:
    """Fire a one-off heartbeat run immediately (the market-monitor tripwire).
    Skips if a trigger is already pending/running so a volatile day can't stack
    investigations, and for users inactive >72h (the recurring heartbeat is
    likewise gated — it resumes when they return). Returns True if enqueued."""
    from services.agent_events import is_user_active
    if not await is_user_active(user_id):
        return False
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
            run_at=datetime.now(timezone.utc), recurrence=None,
            status="pending", system_key=HEARTBEAT_TRIGGER, activity_gated=True,
        ))
        await db.commit()
    logger.info(f"Heartbeat tripwire enqueued for {user_id}: {reason}")
    return True
