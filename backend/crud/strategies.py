"""
CRUD operations for Strategies

Handles database operations for strategies and executions.
"""
from typing import Optional, List
from datetime import datetime, timezone
import uuid
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_
from sqlalchemy.orm import selectinload

from models.db import Strategy, StrategyExecution, ChatFile
from models.strategies import (
    CreateStrategyRequest,
    UpdateStrategyRequest,
    StrategyConfig,
    StrategyStats,
    ExecutionData,
    ExecutionAction,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Strategy CRUD
# ============================================================================

async def create_strategy(
    db: AsyncSession,
    user_id: str,
    request: CreateStrategyRequest
) -> Strategy:
    """Create a new strategy"""
    strategy_id = str(uuid.uuid4())
    
    config = StrategyConfig(
        description=request.description,
        source_chat_id=request.source_chat_id,
        file_ids=request.file_ids,
        entrypoint=request.entrypoint,
        schedule=request.schedule,
        schedule_description=request.schedule_description,
        risk_limits=request.risk_limits,
    )
    
    stats = StrategyStats()
    
    strategy = Strategy(
        id=strategy_id,
        user_id=user_id,
        name=request.name,
        enabled=False,  # Always start disabled
        approved=False,  # Always requires approval
        config=config.model_dump(mode="json"),
        stats=stats.model_dump(mode="json"),
    )
    
    db.add(strategy)
    await db.commit()
    await db.refresh(strategy)
    
    logger.info(f"Created strategy '{request.name}' (id={strategy_id}) for user {user_id}")
    return strategy


async def get_strategy(
    db: AsyncSession,
    strategy_id: str,
    user_id: Optional[str] = None
) -> Optional[Strategy]:
    """Get a strategy by ID, optionally filtering by user"""
    query = select(Strategy).where(Strategy.id == strategy_id)
    if user_id:
        query = query.where(Strategy.user_id == user_id)
    
    result = await db.execute(query)
    return result.scalars().first()


async def list_strategies(
    db: AsyncSession,
    user_id: str,
    enabled_only: bool = False
) -> List[Strategy]:
    """List all strategies for a user"""
    query = select(Strategy).where(Strategy.user_id == user_id)
    if enabled_only:
        query = query.where(Strategy.enabled == True)
    query = query.order_by(Strategy.created_at.desc())
    
    result = await db.execute(query)
    return list(result.scalars().all())


async def update_strategy(
    db: AsyncSession,
    strategy_id: str,
    user_id: str,
    request: UpdateStrategyRequest
) -> Optional[Strategy]:
    """Update a strategy"""
    strategy = await get_strategy(db, strategy_id, user_id)
    if not strategy:
        return None
    
    # Update top-level fields
    if request.name is not None:
        strategy.name = request.name
    if request.enabled is not None:
        # Can only enable if approved
        if request.enabled and not strategy.approved:
            raise ValueError("Cannot enable strategy that is not approved")
        strategy.enabled = request.enabled
    
    # Update config fields
    config = dict(strategy.config or {})
    if request.description is not None:
        config["description"] = request.description
    if request.schedule is not None:
        config["schedule"] = request.schedule
    if request.schedule_description is not None:
        config["schedule_description"] = request.schedule_description
    if request.risk_limits is not None:
        config["risk_limits"] = request.risk_limits.model_dump(mode="json")
    
    strategy.config = config
    
    await db.commit()
    await db.refresh(strategy)
    
    logger.info(f"Updated strategy {strategy_id}")
    return strategy


async def approve_strategy(
    db: AsyncSession,
    strategy_id: str,
    user_id: str
) -> Optional[Strategy]:
    """Approve a strategy for execution"""
    strategy = await get_strategy(db, strategy_id, user_id)
    if not strategy:
        return None
    
    strategy.approved = True
    config = dict(strategy.config or {})
    config["approved_at"] = datetime.now(timezone.utc).isoformat()
    strategy.config = config
    
    await db.commit()
    await db.refresh(strategy)
    
    logger.info(f"Approved strategy {strategy_id}")
    return strategy


async def delete_strategy(
    db: AsyncSession,
    strategy_id: str,
    user_id: str
) -> bool:
    """Delete a strategy"""
    strategy = await get_strategy(db, strategy_id, user_id)
    if not strategy:
        return False
    
    await db.delete(strategy)
    await db.commit()
    
    logger.info(f"Deleted strategy {strategy_id}")
    return True


async def update_strategy_stats(
    db: AsyncSession,
    strategy_id: str,
    execution: "StrategyExecution"
) -> None:
    """Update strategy stats after an execution"""
    strategy = await get_strategy(db, strategy_id)
    if not strategy:
        return
    
    stats = dict(strategy.stats or {})
    data = execution.data or {}
    
    # Update run counts
    stats["total_runs"] = stats.get("total_runs", 0) + 1
    if execution.status == "success":
        stats["successful_runs"] = stats.get("successful_runs", 0) + 1
    else:
        stats["failed_runs"] = stats.get("failed_runs", 0) + 1
    
    # Update last run info
    stats["last_run_at"] = execution.started_at.isoformat()
    stats["last_run_status"] = execution.status
    stats["last_run_summary"] = data.get("summary")
    
    strategy.stats = stats
    await db.commit()


# ============================================================================
# Execution CRUD
# ============================================================================

async def create_execution(
    db: AsyncSession,
    strategy: Strategy,
    trigger: str  # 'scheduled', 'manual', 'dry_run'
) -> StrategyExecution:
    """Create a new execution record (status=running)"""
    execution = StrategyExecution(
        id=uuid.uuid4(),
        strategy_id=strategy.id,
        user_id=strategy.user_id,
        status="running",
        started_at=datetime.now(timezone.utc),
        data={"trigger": trigger, "logs": [], "actions": []},
    )
    
    db.add(execution)
    await db.commit()
    await db.refresh(execution)
    
    return execution


async def complete_execution(
    db: AsyncSession,
    execution: StrategyExecution,
    status: str,  # 'success' or 'failed'
    result: Optional[dict] = None,
    error: Optional[str] = None,
    summary: Optional[str] = None,
    actions: Optional[List[ExecutionAction]] = None,
    logs: Optional[List[str]] = None
) -> StrategyExecution:
    """Complete an execution with results"""
    execution.status = status
    
    data = dict(execution.data or {})
    data["completed_at"] = datetime.now(timezone.utc).isoformat()
    data["duration_ms"] = int(
        (datetime.now(timezone.utc) - execution.started_at).total_seconds() * 1000
    )
    
    if result is not None:
        data["result"] = result
    if error is not None:
        data["error"] = error
    if summary is not None:
        data["summary"] = summary
    if actions is not None:
        data["actions"] = [a.model_dump(mode="json") for a in actions]
    if logs is not None:
        data["logs"] = logs
    
    execution.data = data
    
    await db.commit()
    await db.refresh(execution)
    
    # Update strategy stats
    await update_strategy_stats(db, execution.strategy_id, execution)
    
    return execution


async def get_execution(
    db: AsyncSession,
    execution_id: str,
    user_id: Optional[str] = None
) -> Optional[StrategyExecution]:
    """Get an execution by ID"""
    query = select(StrategyExecution).where(StrategyExecution.id == execution_id)
    if user_id:
        query = query.where(StrategyExecution.user_id == user_id)
    
    result = await db.execute(query)
    return result.scalars().first()


async def list_executions(
    db: AsyncSession,
    strategy_id: str,
    limit: int = 20
) -> List[StrategyExecution]:
    """List recent executions for a strategy"""
    query = (
        select(StrategyExecution)
        .where(StrategyExecution.strategy_id == strategy_id)
        .order_by(StrategyExecution.started_at.desc())
        .limit(limit)
    )
    
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_due_strategies(db: AsyncSession) -> List[Strategy]:
    """
    Get strategies that are due to run based on their schedule.
    
    This is a simplified version - in production you'd want to:
    - Parse cron expressions properly
    - Track last scheduled run vs actual run
    - Handle timezone conversions
    
    For now, returns all enabled+approved strategies (scheduler handles timing)
    """
    query = (
        select(Strategy)
        .where(
            and_(
                Strategy.enabled == True,
                Strategy.approved == True,
            )
        )
    )
    
    result = await db.execute(query)
    return list(result.scalars().all())


# ============================================================================
# File loading (for execution)
# ============================================================================

async def load_strategy_files(
    db: AsyncSession,
    strategy: Strategy
) -> dict[str, str]:
    """
    Load strategy code files from ChatFile table
    
    Returns:
        Dict mapping filename -> content
    """
    config = strategy.config or {}
    file_ids = config.get("file_ids", [])
    
    if not file_ids:
        raise ValueError(f"Strategy {strategy.id} has no file_ids configured")
    
    # Query ChatFile table
    from models.db import ChatFile
    query = select(ChatFile).where(ChatFile.id.in_(file_ids))
    result = await db.execute(query)
    files = result.scalars().all()
    
    # Build filename -> content mapping
    file_map = {}
    for f in files:
        if f.content:  # Skip image files
            file_map[f.filename] = f.content
    
    # Verify entrypoint exists
    entrypoint = config.get("entrypoint", "strategy.py")
    if entrypoint not in file_map:
        raise ValueError(f"Entrypoint '{entrypoint}' not found in strategy files")
    
    return file_map
