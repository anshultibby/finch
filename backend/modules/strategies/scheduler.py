"""
Strategy Scheduler - Background task for scheduled execution

Handles:
- Checking which strategies are due to run
- Executing them on schedule
- Alerting on failures
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from croniter import croniter
from sqlalchemy.ext.asyncio import AsyncSession

from database import AsyncSessionLocal
from models.db import Strategy
from crud.strategies import get_due_strategies, get_strategy
from .executor import execute_strategy

logger = logging.getLogger(__name__)


class StrategyScheduler:
    """
    Background scheduler for strategy execution
    
    Runs in a loop, checking every minute for strategies that need to run.
    
    Usage:
        scheduler = StrategyScheduler()
        await scheduler.start()  # Runs forever
        
        # Or run once for testing:
        await scheduler.run_once()
    """
    
    def __init__(self, check_interval_seconds: int = 60):
        self.check_interval = check_interval_seconds
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """Start the scheduler loop"""
        if self._running:
            logger.warning("Scheduler already running")
            return
        
        self._running = True
        logger.info("Strategy scheduler started")
        
        while self._running:
            try:
                await self.run_once()
            except Exception as e:
                logger.exception(f"Scheduler error: {e}")
            
            await asyncio.sleep(self.check_interval)
    
    async def stop(self) -> None:
        """Stop the scheduler"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Strategy scheduler stopped")
    
    async def run_once(self) -> None:
        """Run one iteration of the scheduler"""
        async with AsyncSessionLocal() as db:
            strategies = await get_due_strategies(db)
            
            for strategy in strategies:
                if self._should_run_now(strategy):
                    await self._execute_strategy(db, strategy)
    
    def _should_run_now(self, strategy: Strategy) -> bool:
        """
        Check if a strategy should run now based on its schedule
        
        Uses croniter to check if the current minute matches the schedule.
        """
        config = strategy.config or {}
        schedule = config.get("schedule")
        
        if not schedule:
            # No schedule = manual only
            return False
        
        try:
            # Check if current minute matches cron schedule
            now = datetime.now(timezone.utc)
            cron = croniter(schedule, now)
            
            # Get previous scheduled time
            prev_time = cron.get_prev(datetime)
            
            # If previous scheduled time is within the last minute, we should run
            # (This handles the case where we check at :00 and schedule is "0 * * * *")
            diff_seconds = (now - prev_time).total_seconds()
            
            if diff_seconds < self.check_interval:
                # Check if we already ran this schedule
                stats = strategy.stats or {}
                last_run = stats.get("last_run_at")
                
                if last_run:
                    last_run_dt = datetime.fromisoformat(last_run.replace("Z", "+00:00"))
                    # Don't run if we ran in the last minute
                    if (now - last_run_dt).total_seconds() < self.check_interval:
                        return False
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Invalid cron schedule '{schedule}' for strategy {strategy.id}: {e}")
            return False
    
    async def _execute_strategy(self, db: AsyncSession, strategy: Strategy) -> None:
        """Execute a single strategy"""
        logger.info(f"Running scheduled strategy: {strategy.name} ({strategy.id})")
        
        try:
            execution = await execute_strategy(
                db=db,
                strategy=strategy,
                trigger="scheduled",
                dry_run=False  # Scheduled runs are live
            )
            
            if execution.status == "failed":
                await self._send_alert(strategy, execution)
                
        except Exception as e:
            logger.exception(f"Failed to execute strategy {strategy.id}: {e}")
            await self._send_alert(strategy, error=str(e))
    
    async def _send_alert(
        self,
        strategy: Strategy,
        execution: Optional["StrategyExecution"] = None,
        error: Optional[str] = None
    ) -> None:
        """
        Send alert when a strategy fails
        
        TODO: Implement actual alerting (email, push notification, etc.)
        For now, just logs.
        """
        error_msg = error or (execution.data.get("error") if execution else "Unknown error")
        
        logger.warning(
            f"🚨 Strategy '{strategy.name}' failed: {error_msg}",
            extra={
                "strategy_id": strategy.id,
                "user_id": strategy.user_id,
                "error": error_msg,
            }
        )
        
        # TODO: Send notification to user
        # - Email
        # - Push notification
        # - In-app notification


# Global scheduler instance
_scheduler: Optional[StrategyScheduler] = None


def get_scheduler() -> StrategyScheduler:
    """Get or create the global scheduler instance"""
    global _scheduler
    if _scheduler is None:
        _scheduler = StrategyScheduler()
    return _scheduler


async def start_scheduler() -> None:
    """Start the global scheduler (call from app startup)"""
    scheduler = get_scheduler()
    asyncio.create_task(scheduler.start())


async def stop_scheduler() -> None:
    """Stop the global scheduler (call from app shutdown)"""
    global _scheduler
    if _scheduler:
        await _scheduler.stop()
        _scheduler = None
