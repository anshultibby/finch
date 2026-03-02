"""
CRUD operations for Strategies and StrategyFiles.

Strategies own their code in the strategy_files table (not ChatFile).
"""
from typing import Optional, List
from datetime import datetime, timezone
import uuid
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from models.db import Strategy, StrategyExecution, StrategyFile
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
    request: CreateStrategyRequest,
) -> Strategy:
    """Create a new strategy and write its files to strategy_files table."""
    strategy_id = str(uuid.uuid4())

    config = StrategyConfig(
        platform=request.platform,
        description=request.description,
        thesis=request.thesis,
        source_chat_id=request.source_chat_id,
        schedule=request.schedule,
        schedule_description=request.schedule_description,
        capital=request.capital,
        risk_limits=request.risk_limits,
    )

    strategy = Strategy(
        id=strategy_id,
        user_id=user_id,
        name=request.name,
        enabled=False,
        approved=False,
        config=config.model_dump(mode="json"),
        stats=StrategyStats().model_dump(mode="json"),
    )
    db.add(strategy)

    # Write code files owned directly by this strategy
    for filename, content in request.files.items():
        db.add(StrategyFile(
            id=str(uuid.uuid4()),
            strategy_id=strategy_id,
            filename=filename,
            content=content,
        ))

    await db.commit()
    await db.refresh(strategy)
    logger.info(f"Created strategy '{request.name}' (id={strategy_id}) for user {user_id}")
    return strategy


async def get_strategy(
    db: AsyncSession,
    strategy_id: str,
    user_id: Optional[str] = None,
) -> Optional[Strategy]:
    query = select(Strategy).where(Strategy.id == strategy_id)
    if user_id:
        query = query.where(Strategy.user_id == user_id)
    result = await db.execute(query)
    return result.scalars().first()


async def list_strategies(
    db: AsyncSession,
    user_id: str,
    enabled_only: bool = False,
) -> List[Strategy]:
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
    request: UpdateStrategyRequest,
) -> Optional[Strategy]:
    strategy = await get_strategy(db, strategy_id, user_id)
    if not strategy:
        return None

    if request.name is not None:
        strategy.name = request.name
    if request.enabled is not None:
        if request.enabled and not strategy.approved:
            raise ValueError("Cannot enable strategy that is not approved")
        strategy.enabled = request.enabled

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

    # Update code files if provided
    if request.files:
        for filename, content in request.files.items():
            result = await db.execute(
                select(StrategyFile).where(
                    StrategyFile.strategy_id == strategy_id,
                    StrategyFile.filename == filename,
                )
            )
            file_row = result.scalar_one_or_none()
            if file_row:
                file_row.content = content
            else:
                db.add(StrategyFile(
                    id=str(uuid.uuid4()),
                    strategy_id=strategy_id,
                    filename=filename,
                    content=content,
                ))

    await db.commit()
    await db.refresh(strategy)
    logger.info(f"Updated strategy {strategy_id}")
    return strategy


async def approve_strategy(
    db: AsyncSession,
    strategy_id: str,
    user_id: str,
) -> Optional[Strategy]:
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
    user_id: str,
) -> bool:
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
    execution: "StrategyExecution",
) -> None:
    strategy = await get_strategy(db, strategy_id)
    if not strategy:
        return

    stats = dict(strategy.stats or {})
    data = execution.data or {}

    stats["total_runs"] = stats.get("total_runs", 0) + 1
    if execution.status == "success":
        stats["successful_runs"] = stats.get("successful_runs", 0) + 1
    else:
        stats["failed_runs"] = stats.get("failed_runs", 0) + 1

    stats["last_run_at"] = execution.started_at.isoformat()
    stats["last_run_status"] = execution.status
    stats["last_run_summary"] = data.get("summary")

    strategy.stats = stats
    await db.commit()


# ============================================================================
# StrategyFile CRUD
# ============================================================================

async def get_strategy_files(
    db: AsyncSession,
    strategy_id: str,
) -> List[StrategyFile]:
    """Return all files for a strategy."""
    result = await db.execute(
        select(StrategyFile).where(StrategyFile.strategy_id == strategy_id)
    )
    return list(result.scalars().all())


async def load_strategy_files(
    db: AsyncSession,
    strategy: Strategy,
) -> dict[str, str]:
    """Load strategy code files. Returns filename -> content mapping."""
    files = await get_strategy_files(db, strategy.id)
    if not files:
        raise ValueError(f"Strategy {strategy.id} has no files")
    return {f.filename: f.content for f in files}


# ============================================================================
# Execution CRUD
# ============================================================================

async def create_execution(
    db: AsyncSession,
    strategy: Strategy,
    trigger: str,
) -> StrategyExecution:
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
    status: str,
    result: Optional[dict] = None,
    error: Optional[str] = None,
    summary: Optional[str] = None,
    actions: Optional[List[ExecutionAction]] = None,
    logs: Optional[List[str]] = None,
) -> StrategyExecution:
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

    await update_strategy_stats(db, execution.strategy_id, execution)
    return execution


async def get_execution(
    db: AsyncSession,
    execution_id: str,
    user_id: Optional[str] = None,
) -> Optional[StrategyExecution]:
    query = select(StrategyExecution).where(StrategyExecution.id == execution_id)
    if user_id:
        query = query.where(StrategyExecution.user_id == user_id)
    result = await db.execute(query)
    return result.scalars().first()


async def list_executions(
    db: AsyncSession,
    strategy_id: str,
    limit: int = 20,
) -> List[StrategyExecution]:
    query = (
        select(StrategyExecution)
        .where(StrategyExecution.strategy_id == strategy_id)
        .order_by(StrategyExecution.started_at.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_due_strategies(db: AsyncSession) -> List[Strategy]:
    """Return all enabled+approved strategies (scheduler handles timing)."""
    query = select(Strategy).where(
        and_(Strategy.enabled == True, Strategy.approved == True)
    )
    result = await db.execute(query)
    return list(result.scalars().all())
