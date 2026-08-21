"""Stale chat-processing flag reaper.

`chats.is_processing` is set true when a turn starts and reset false when it
finishes. But if the generation dies mid-turn — stream drop, LLM timeout, worker
restart, deploy — the reset at the end of the flow never runs and the flag leaks
`true` forever, so the UI shows a chat stuck "thinking" with no output.

There is already a *lazy* cleanup in `is_chat_processing` (resets flags >5 min
old), but it only fires when someone polls `/chat/status` for that specific chat.
A stuck chat whose owner never reopens it — or whose client keeps waiting on a
silently-dead SSE stream — is never swept. This background loop closes that gap:
it resets any flag older than the (conservative) threshold, regardless of polling.

The threshold is deliberately generous (20 min) so it only ever touches truly
dead flags — live streams have their own 180–600s silence timeouts, so a genuine
generation never stays quiet this long. Idempotent; safe to run repeatedly.
Wired into app startup in main.py.
"""
import asyncio
import logging
import os

logger = logging.getLogger(__name__)

# Tunable without a deploy. Default: reset flags stuck >20 min, scan every 5 min.
STALE_MINUTES = int(os.getenv("PROCESSING_REAP_STALE_MINUTES", "20"))
REAP_INTERVAL_SECONDS = int(os.getenv("PROCESSING_REAP_INTERVAL_SECONDS", str(5 * 60)))


async def reap_stale_processing() -> int:
    """Reset is_processing on chats stuck processing beyond the threshold.
    Returns the number of chats cleared."""
    from core.database import get_db_session
    from sqlalchemy import text

    async with get_db_session() as db:
        result = await db.execute(
            text(
                """
                UPDATE chats
                   SET is_processing = false, processing_started_at = null
                 WHERE is_processing = true
                   AND processing_started_at < now() - make_interval(mins => :mins)
                RETURNING chat_id
                """
            ),
            {"mins": STALE_MINUTES},
        )
        rows = result.fetchall()
        await db.commit()
        if rows:
            logger.info(
                f"[processing-reaper] cleared {len(rows)} stale is_processing flag(s) "
                f"(>{STALE_MINUTES}m): {', '.join(r[0] for r in rows[:10])}"
                + (" …" if len(rows) > 10 else "")
            )
        return len(rows)


async def run_processing_reaper_loop():
    """Run forever, scanning every REAP_INTERVAL_SECONDS. No persistent state —
    the query is idempotent, so it survives restarts."""
    logger.info(
        f"Chat processing-flag reaper started "
        f"(threshold={STALE_MINUTES}m, interval={REAP_INTERVAL_SECONDS}s)"
    )
    while True:
        try:
            await reap_stale_processing()
        except Exception as e:
            logger.error(f"Processing reaper loop error: {e}")
        await asyncio.sleep(REAP_INTERVAL_SECONDS)
