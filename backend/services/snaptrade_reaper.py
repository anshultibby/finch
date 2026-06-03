"""Stale SnapTrade connection reaper.

SnapTrade bills per registered user. This background task de-registers users who
haven't logged into Finch (auth.users.last_sign_in_at) within the inactivity
threshold, so we stop paying for dormant connections. It is a *soft* purge:
the local snaptrade_users row and the user's cached portfolio are kept, and the
row is flagged (purged_at) so the UI can show a "reconnect to refresh" caution
with their last-known value. Reconnecting clears the flag (see
SnapTradeTools._save_session).

Idempotent and safe to run repeatedly: already-purged rows (purged_at IS NOT
NULL) and active users are skipped. Wired into app startup in main.py.
"""
import asyncio
import logging
import os
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

# Tunable without a deploy. Default: 30 days inactive, scan every 6 hours.
INACTIVITY_DAYS = int(os.getenv("SNAPTRADE_REAP_INACTIVITY_DAYS", "30"))
REAP_INTERVAL_SECONDS = int(os.getenv("SNAPTRADE_REAP_INTERVAL_SECONDS", str(6 * 3600)))


async def find_stale_user_ids() -> list[str]:
    """
    Connected, never-purged SnapTrade users whose most recent Finch activity is
    older than the threshold. "Activity" = the most recent of Supabase login,
    SnapTrade activity, and registration date — so we never purge someone who is
    actively using the app even if one signal is stale.
    """
    from core.database import get_db_session
    from sqlalchemy import text

    cutoff = datetime.now(timezone.utc) - timedelta(days=INACTIVITY_DAYS)
    async with get_db_session() as db:
        result = await db.execute(
            text(
                """
                SELECT s.user_id
                FROM snaptrade_users s
                LEFT JOIN auth.users u ON u.id::text = s.user_id
                WHERE s.is_connected = true
                  AND s.purged_at IS NULL
                  AND GREATEST(
                        COALESCE(u.last_sign_in_at, 'epoch'::timestamptz),
                        COALESCE(s.last_activity,   'epoch'::timestamptz),
                        COALESCE(s.created_at,      'epoch'::timestamptz)
                      ) < :cutoff
                """
            ),
            {"cutoff": cutoff},
        )
        return [row[0] for row in result.fetchall()]


async def reap_stale_connections() -> int:
    """Run one reaping pass. Returns the number of connections purged."""
    from modules.tools.clients.snaptrade import snaptrade_tools

    user_ids = await find_stale_user_ids()
    if not user_ids:
        return 0

    logger.info(
        f"[snaptrade-reaper] {len(user_ids)} stale connection(s) to purge "
        f"(>{INACTIVITY_DAYS}d inactive)"
    )
    purged = 0
    for user_id in user_ids:
        try:
            res = await snaptrade_tools.soft_purge_stale_user(user_id)
            purged += 1
            logger.info(
                f"[snaptrade-reaper] purged {user_id} "
                f"(last_portfolio_value={res.get('last_portfolio_value')})"
            )
        except Exception as e:
            logger.error(f"[snaptrade-reaper] failed to purge {user_id}: {e}")
    return purged


async def run_reaper_loop():
    """Run forever, scanning every REAP_INTERVAL_SECONDS. Survives restarts via
    its idempotent query (no persistent 'last run' state needed)."""
    logger.info(
        f"SnapTrade stale-connection reaper started "
        f"(threshold={INACTIVITY_DAYS}d, interval={REAP_INTERVAL_SECONDS}s)"
    )
    while True:
        try:
            await reap_stale_connections()
        except Exception as e:
            logger.error(f"Reaper loop error: {e}")
        await asyncio.sleep(REAP_INTERVAL_SECONDS)
