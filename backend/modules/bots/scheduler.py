"""
Bot Scheduler — checks for due wakeups and executes them.

Replaces the old cron-based tick scheduler. Bots schedule their own
wakeups via the `schedule_wakeup` tool, and this loop fires them.
"""
import asyncio
import logging
from typing import Optional

from core.database import get_db_session
from crud.bots import get_due_wakeups
from .wakeup_executor import execute_wakeup

logger = logging.getLogger(__name__)

# Per-bot locks to prevent concurrent wakeup/chat execution on the same bot
_bot_locks: dict[str, asyncio.Lock] = {}

MAX_CONCURRENT_WAKEUPS = 10


def get_bot_lock(bot_id: str) -> asyncio.Lock:
    """Get or create a per-bot asyncio lock."""
    if bot_id not in _bot_locks:
        _bot_locks[bot_id] = asyncio.Lock()
    return _bot_locks[bot_id]


class BotScheduler:
    """Background scheduler that checks for and executes due bot wakeups."""

    def __init__(self, check_interval_seconds: int = 30):
        self.check_interval = check_interval_seconds
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._semaphore = asyncio.Semaphore(MAX_CONCURRENT_WAKEUPS)

    async def start(self) -> None:
        if self._running:
            logger.warning("Bot scheduler already running")
            return
        self._running = True
        logger.info("Bot wakeup scheduler started (interval=%ds)", self.check_interval)
        await self._run_loop()

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Bot wakeup scheduler stopped")

    async def run_once(self) -> None:
        """Check for due wakeups and fire them concurrently.

        Each wakeup runs in its own DB session (via execute_wakeup)
        so the scheduler session is only held for the brief query.

        Uses per-bot locks to prevent concurrent execution on the same bot,
        and a global semaphore to cap total concurrent wakeups.
        """
        async with get_db_session() as db:
            wakeups = await get_due_wakeups(db)
            if not wakeups:
                return
            logger.info("Found %d due wakeup(s)", len(wakeups))

        async def _run_one(wakeup):
            bot_lock = get_bot_lock(wakeup.bot_id)

            async with self._semaphore:
                async with bot_lock:
                    try:
                        async with get_db_session() as db:
                            wakeup_merged = await db.merge(wakeup)
                            chat_id = await execute_wakeup(db, wakeup_merged)
                        if chat_id:
                            logger.info(
                                "Wakeup %s executed → chat %s (bot=%s, reason=%s)",
                                wakeup.id, chat_id, wakeup.bot_id, wakeup.reason[:60],
                            )
                    except Exception as e:
                        logger.exception("Failed to execute wakeup %s: %s", wakeup.id, e)

        await asyncio.gather(*[_run_one(w) for w in wakeups])

    async def _run_loop(self) -> None:
        while self._running:
            try:
                await self.run_once()
            except Exception as e:
                logger.exception("Bot scheduler loop error: %s", e)
            await asyncio.sleep(self.check_interval)


_scheduler: Optional[BotScheduler] = None


def get_scheduler() -> BotScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = BotScheduler()
    return _scheduler


async def start_scheduler() -> None:
    scheduler = get_scheduler()
    asyncio.create_task(scheduler.start())


async def stop_scheduler() -> None:
    global _scheduler
    if _scheduler:
        await _scheduler.stop()
        _scheduler = None
