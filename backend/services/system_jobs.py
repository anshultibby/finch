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
    "write_plan(), append_note(). Place no orders. If the user has never traded "
    "and has no journal, keep it to a one-paragraph plan and stop — stay cheap."
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
    except Exception as e:
        # Provisioning must never break the connect flow.
        logger.error(f"Failed to provision {DAY_TRADING_NIGHTLY} for {user_id}: {e}")
