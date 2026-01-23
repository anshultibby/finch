"""
API routes for Strategies

Provides endpoints for:
- CRUD operations on strategies
- Running strategies (manual/dry run)
- Viewing execution history
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_async_db
from crud import strategies as crud
from models.strategies import (
    CreateStrategyRequest,
    UpdateStrategyRequest,
    StrategyResponse,
    StrategyDetailResponse,
    ExecutionResponse,
    ExecutionDetailResponse,
    RunStrategyRequest,
    RunStrategyResponse,
    StrategyConfig,
    StrategyStats,
    ExecutionData,
    ExecutionAction,
)
from modules.strategies.executor import execute_strategy

router = APIRouter(prefix="/strategies", tags=["strategies"])


def _get_user_id(x_user_id: str = Header(..., alias="X-User-ID")) -> str:
    """Extract user ID from header"""
    return x_user_id


def _strategy_to_response(strategy) -> StrategyResponse:
    """Convert Strategy ORM to response"""
    config = strategy.config or {}
    stats = strategy.stats or {}
    
    return StrategyResponse(
        id=strategy.id,
        name=strategy.name,
        description=config.get("description", ""),
        enabled=strategy.enabled,
        approved=strategy.approved,
        schedule_description=config.get("schedule_description"),
        total_runs=stats.get("total_runs", 0),
        successful_runs=stats.get("successful_runs", 0),
        last_run_at=stats.get("last_run_at"),
        last_run_status=stats.get("last_run_status"),
        last_run_summary=stats.get("last_run_summary"),
        created_at=strategy.created_at,
        updated_at=strategy.updated_at,
    )


def _strategy_to_detail_response(strategy) -> StrategyDetailResponse:
    """Convert Strategy ORM to detailed response"""
    config = strategy.config or {}
    stats_dict = strategy.stats or {}
    
    return StrategyDetailResponse(
        id=strategy.id,
        name=strategy.name,
        description=config.get("description", ""),
        enabled=strategy.enabled,
        approved=strategy.approved,
        schedule_description=config.get("schedule_description"),
        total_runs=stats_dict.get("total_runs", 0),
        successful_runs=stats_dict.get("successful_runs", 0),
        last_run_at=stats_dict.get("last_run_at"),
        last_run_status=stats_dict.get("last_run_status"),
        last_run_summary=stats_dict.get("last_run_summary"),
        created_at=strategy.created_at,
        updated_at=strategy.updated_at,
        source_chat_id=config.get("source_chat_id"),
        file_ids=config.get("file_ids", []),
        entrypoint=config.get("entrypoint", "strategy.py"),
        schedule=config.get("schedule"),
        risk_limits=config.get("risk_limits"),
        stats=StrategyStats(**stats_dict),
    )


def _execution_to_response(execution) -> ExecutionResponse:
    """Convert StrategyExecution ORM to response"""
    data = execution.data or {}
    
    return ExecutionResponse(
        id=str(execution.id),
        strategy_id=execution.strategy_id,
        status=execution.status,
        started_at=execution.started_at,
        completed_at=data.get("completed_at"),
        trigger=data.get("trigger", "unknown"),
        summary=data.get("summary"),
        error=data.get("error"),
        actions_count=len(data.get("actions", [])),
    )


def _execution_to_detail_response(execution) -> ExecutionDetailResponse:
    """Convert StrategyExecution ORM to detailed response"""
    data = execution.data or {}
    
    actions = [
        ExecutionAction(**a) for a in data.get("actions", [])
    ]
    
    return ExecutionDetailResponse(
        id=str(execution.id),
        strategy_id=execution.strategy_id,
        status=execution.status,
        started_at=execution.started_at,
        completed_at=data.get("completed_at"),
        trigger=data.get("trigger", "unknown"),
        summary=data.get("summary"),
        error=data.get("error"),
        actions_count=len(actions),
        duration_ms=data.get("duration_ms"),
        logs=data.get("logs", []),
        actions=actions,
        result=data.get("result"),
    )


# ============================================================================
# Strategy CRUD
# ============================================================================

@router.post("", response_model=StrategyDetailResponse)
async def create_strategy(
    request: CreateStrategyRequest,
    user_id: str = Depends(_get_user_id),
    db: AsyncSession = Depends(get_async_db)
):
    """Create a new strategy"""
    strategy = await crud.create_strategy(db, user_id, request)
    return _strategy_to_detail_response(strategy)


@router.get("", response_model=List[StrategyResponse])
async def list_strategies(
    enabled_only: bool = False,
    user_id: str = Depends(_get_user_id),
    db: AsyncSession = Depends(get_async_db)
):
    """List all strategies for the current user"""
    strategies = await crud.list_strategies(db, user_id, enabled_only)
    return [_strategy_to_response(s) for s in strategies]


@router.get("/{strategy_id}", response_model=StrategyDetailResponse)
async def get_strategy(
    strategy_id: str,
    user_id: str = Depends(_get_user_id),
    db: AsyncSession = Depends(get_async_db)
):
    """Get a specific strategy"""
    strategy = await crud.get_strategy(db, strategy_id, user_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return _strategy_to_detail_response(strategy)


@router.patch("/{strategy_id}", response_model=StrategyDetailResponse)
async def update_strategy(
    strategy_id: str,
    request: UpdateStrategyRequest,
    user_id: str = Depends(_get_user_id),
    db: AsyncSession = Depends(get_async_db)
):
    """Update a strategy"""
    try:
        strategy = await crud.update_strategy(db, strategy_id, user_id, request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return _strategy_to_detail_response(strategy)


@router.delete("/{strategy_id}")
async def delete_strategy(
    strategy_id: str,
    user_id: str = Depends(_get_user_id),
    db: AsyncSession = Depends(get_async_db)
):
    """Delete a strategy"""
    success = await crud.delete_strategy(db, strategy_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return {"success": True}


@router.post("/{strategy_id}/approve", response_model=StrategyDetailResponse)
async def approve_strategy(
    strategy_id: str,
    user_id: str = Depends(_get_user_id),
    db: AsyncSession = Depends(get_async_db)
):
    """Approve a strategy for execution"""
    strategy = await crud.approve_strategy(db, strategy_id, user_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return _strategy_to_detail_response(strategy)


# ============================================================================
# Strategy Execution
# ============================================================================

@router.post("/{strategy_id}/run", response_model=RunStrategyResponse)
async def run_strategy(
    strategy_id: str,
    request: RunStrategyRequest = RunStrategyRequest(),
    user_id: str = Depends(_get_user_id),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Manually run a strategy
    
    - dry_run=True (default): Simulate without real trades
    - dry_run=False: Execute real trades (requires approval)
    """
    strategy = await crud.get_strategy(db, strategy_id, user_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    # Check approval for live runs
    if not request.dry_run and not strategy.approved:
        raise HTTPException(
            status_code=400,
            detail="Strategy must be approved before live execution"
        )
    
    trigger = "dry_run" if request.dry_run else "manual"
    execution = await execute_strategy(
        db=db,
        strategy=strategy,
        trigger=trigger,
        dry_run=request.dry_run
    )
    
    data = execution.data or {}
    actions = [ExecutionAction(**a) for a in data.get("actions", [])]
    
    return RunStrategyResponse(
        execution_id=str(execution.id),
        status=execution.status,
        summary=data.get("summary"),
        actions=actions,
        error=data.get("error"),
    )


@router.get("/{strategy_id}/executions", response_model=List[ExecutionResponse])
async def list_executions(
    strategy_id: str,
    limit: int = 20,
    user_id: str = Depends(_get_user_id),
    db: AsyncSession = Depends(get_async_db)
):
    """List recent executions for a strategy"""
    # Verify ownership
    strategy = await crud.get_strategy(db, strategy_id, user_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    executions = await crud.list_executions(db, strategy_id, limit)
    return [_execution_to_response(e) for e in executions]


@router.get("/{strategy_id}/executions/{execution_id}", response_model=ExecutionDetailResponse)
async def get_execution(
    strategy_id: str,
    execution_id: str,
    user_id: str = Depends(_get_user_id),
    db: AsyncSession = Depends(get_async_db)
):
    """Get detailed execution info"""
    execution = await crud.get_execution(db, execution_id, user_id)
    if not execution or execution.strategy_id != strategy_id:
        raise HTTPException(status_code=404, detail="Execution not found")
    return _execution_to_detail_response(execution)
