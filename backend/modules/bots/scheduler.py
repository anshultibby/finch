"""
Bot Scheduler - Background task for scheduled bot ticks.
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from croniter import croniter
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db_session
from models.db import TradingBot
from crud.bots import get_due_bots
from .executor import execute_bot_tick

logger = logging.getLogger(__name__)


class BotScheduler:
    """Background scheduler for bot tick execution."""

    def __init__(self, check_interval_seconds: int = 60):
        self.check_interval = check_interval_seconds
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        if self._running:
            logger.warning("Bot scheduler already running")
            return
        self._running = True
        logger.info("Bot scheduler started")
        await self._run_loop()

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Bot scheduler stopped")

    async def run_once(self) -> None:
        async with get_db_session() as db:
            bots = await get_due_bots(db)
            for bot in bots:
                if self._should_run_now(bot):
                    await self._execute_tick(db, bot)

    async def _run_loop(self) -> None:
        while self._running:
            try:
                await self.run_once()
            except Exception as e:
                logger.exception(f"Bot scheduler error: {e}")
            await asyncio.sleep(self.check_interval)

    def _should_run_now(self, bot: TradingBot) -> bool:
        config = bot.config or {}
        schedule = config.get("schedule")
        if not schedule:
            return False

        stats = bot.stats or {}
        last_run = stats.get("last_run_at")
        now = datetime.now(timezone.utc)

        if not last_run:
            try:
                cron = croniter(schedule, now)
                prev = cron.get_prev(datetime)
                return (now - prev).total_seconds() < 3600
            except Exception:
                return True

        try:
            last_run_dt = datetime.fromisoformat(last_run.replace("Z", "+00:00"))
            cron = croniter(schedule, last_run_dt)
            next_run = cron.get_next(datetime)
            return now >= next_run
        except Exception as e:
            logger.warning(f"Error parsing schedule for bot {bot.id}: {e}")
            return False

    async def _execute_tick(self, db: AsyncSession, bot: TradingBot) -> None:
        config = bot.config or {}
        paper_mode = config.get("paper_mode", True)
        logger.info(f"Running scheduled bot tick: {bot.name} ({bot.id}) paper_mode={paper_mode}")

        try:
            execution = await execute_bot_tick(
                db=db,
                bot=bot,
                trigger="scheduled",
                dry_run=paper_mode,
            )
            if execution.status == "failed":
                await self._send_alert(bot, execution)
        except Exception as e:
            logger.exception(f"Failed to execute bot {bot.id}: {e}")
            await self._send_alert(bot, error=str(e))

    async def _send_alert(self, bot: TradingBot, execution=None, error: Optional[str] = None) -> None:
        error_msg = error or (execution.data.get("error") if execution else "Unknown error")
        logger.warning(
            f"Bot '{bot.name}' tick failed: {error_msg}",
            extra={"bot_id": bot.id, "user_id": bot.user_id, "error": error_msg}
        )


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
