"""
Strategy tools for LLM

These tools allow the LLM to:
- Deploy strategies from chat files
- List and manage user strategies
- Run strategies (dry run or live)
- Check strategy status and history

IMPORTANT: The tool descriptions guide the LLM on how to communicate
with users about strategies in plain language.
"""
from typing import Optional, List
import json
from pydantic import BaseModel, Field
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db_session
from modules.agent.context import AgentContext
from crud import strategies as crud
from crud.chat_files import list_chat_files
from models.db import ChatFile
from models.strategies import (
    CreateStrategyRequest,
    UpdateStrategyRequest,
    RiskLimits,
    StrategyInfoForLLM,
)
from modules.strategies.executor import execute_strategy

logger = logging.getLogger(__name__)


# ============================================================================
# Pydantic models for tool parameters
# ============================================================================

class DeployStrategyParams(BaseModel):
    """Parameters for deploy_strategy tool"""
    name: str = Field(..., description="Human-readable strategy name")
    description: str = Field(..., description="Plain-language description of what the strategy does")
    file_ids: List[str] = Field(..., description="List of ChatFile IDs to include")
    entrypoint: str = Field(default="strategy.py", description="Which file to execute")
    schedule: Optional[str] = Field(None, description="Cron expression for scheduled runs")
    schedule_description: Optional[str] = Field(None, description="Human-readable schedule")
    max_order_usd: Optional[float] = Field(None, description="Max USD per order")
    max_daily_usd: Optional[float] = Field(None, description="Max USD per day")


class UpdateStrategyParams(BaseModel):
    """Parameters for update_strategy tool"""
    strategy_id: str
    enabled: Optional[bool] = None
    name: Optional[str] = None
    description: Optional[str] = None
    schedule: Optional[str] = None
    schedule_description: Optional[str] = None
    max_order_usd: Optional[float] = None
    max_daily_usd: Optional[float] = None


class RunStrategyParams(BaseModel):
    """Parameters for run_strategy tool"""
    strategy_id: str
    dry_run: bool = Field(default=True, description="If true, simulate without real trades")


# ============================================================================
# Tool implementations
# ============================================================================

async def deploy_strategy_impl(params: DeployStrategyParams, context: AgentContext) -> dict:
    """
    Deploy chat files as an automated trading strategy.
    
    Creates a strategy record that references the specified ChatFiles.
    The strategy starts disabled and unapproved - user must approve before live trading.
    """
    async with get_db_session() as db:
        files: dict[str, str] = {}
        if params.file_ids:
            result = await db.execute(
                select(ChatFile).where(ChatFile.id.in_(params.file_ids))
            )
            for file_obj in result.scalars().all():
                if file_obj.content:
                    files[file_obj.filename] = file_obj.content

        resolved_entrypoint = params.entrypoint
        if resolved_entrypoint == "strategy.py":
            if "strategy.py" not in files:
                config_content = files.get("config.json")
                if config_content:
                    try:
                        config_data = json.loads(config_content)
                        resolved_entrypoint = (
                            config_data.get("entrypoint")
                            or config_data.get("entry_script")
                            or resolved_entrypoint
                        )
                    except json.JSONDecodeError:
                        resolved_entrypoint = resolved_entrypoint
                elif "entry.py" in files:
                    resolved_entrypoint = "entry.py"

        # Build risk limits if provided
        risk_limits = None
        if params.max_order_usd or params.max_daily_usd:
            risk_limits = RiskLimits(
                max_order_usd=params.max_order_usd,
                max_daily_usd=params.max_daily_usd,
            )
        
        request = CreateStrategyRequest(
            name=params.name,
            description=params.description,
            file_ids=params.file_ids,
            entrypoint=resolved_entrypoint,
            schedule=params.schedule,
            schedule_description=params.schedule_description,
            risk_limits=risk_limits,
            source_chat_id=context.chat_id,
        )
        
        strategy = await crud.create_strategy(db, context.user_id, request)
        
        return {
            "success": True,
            "strategy_id": strategy.id,
            "name": strategy.name,
            "status": "created",
            "needs_approval": True,
            "message": f"Strategy '{strategy.name}' created. It needs to be approved before it can trade with real money."
        }


async def list_strategies_impl(context: AgentContext) -> dict:
    """
    List all strategies for the current user.
    """
    async with get_db_session() as db:
        strategies = await crud.list_strategies(db, context.user_id)
        
        if not strategies:
            return {
                "strategies": [],
                "message": "No strategies found. Create one by describing what you want to automate."
            }
        
        # Convert to LLM-friendly format
        strategy_list = [StrategyInfoForLLM.from_strategy(s).model_dump() for s in strategies]
        
        return {
            "strategies": strategy_list,
            "count": len(strategy_list)
        }


async def get_strategy_impl(strategy_id: str, context: AgentContext) -> dict:
    """
    Get detailed info about a specific strategy.
    """
    async with get_db_session() as db:
        strategy = await crud.get_strategy(db, strategy_id, context.user_id)
        
        if not strategy:
            return {"error": "Strategy not found"}
        
        config = strategy.config or {}
        stats = strategy.stats or {}
        
        # Get recent executions
        executions = await crud.list_executions(db, strategy_id, limit=5)
        
        recent_runs = []
        for ex in executions:
            data = ex.data or {}
            recent_runs.append({
                "time": ex.started_at.isoformat(),
                "status": ex.status,
                "trigger": data.get("trigger"),
                "summary": data.get("summary"),
            })
        
        return {
            "id": strategy.id,
            "name": strategy.name,
            "description": config.get("description", ""),
            "enabled": strategy.enabled,
            "approved": strategy.approved,
            "schedule": config.get("schedule_description"),
            "stats": {
                "total_runs": stats.get("total_runs", 0),
                "successful_runs": stats.get("successful_runs", 0),
                "last_run": stats.get("last_run_summary"),
            },
            "recent_runs": recent_runs,
            "risk_limits": config.get("risk_limits"),
        }


async def update_strategy_impl(params: UpdateStrategyParams, context: AgentContext) -> dict:
    """
    Update a strategy's settings.
    """
    async with get_db_session() as db:
        # Build risk limits if provided
        risk_limits = None
        if params.max_order_usd is not None or params.max_daily_usd is not None:
            # Get existing limits first
            strategy = await crud.get_strategy(db, params.strategy_id, context.user_id)
            if not strategy:
                return {"error": "Strategy not found"}
            
            existing_limits = (strategy.config or {}).get("risk_limits", {})
            risk_limits = RiskLimits(
                max_order_usd=params.max_order_usd if params.max_order_usd is not None else existing_limits.get("max_order_usd"),
                max_daily_usd=params.max_daily_usd if params.max_daily_usd is not None else existing_limits.get("max_daily_usd"),
            )
        
        request = UpdateStrategyRequest(
            name=params.name,
            enabled=params.enabled,
            description=params.description,
            schedule=params.schedule,
            schedule_description=params.schedule_description,
            risk_limits=risk_limits,
        )
        
        try:
            strategy = await crud.update_strategy(db, params.strategy_id, context.user_id, request)
        except ValueError as e:
            return {"error": str(e)}
        
        if not strategy:
            return {"error": "Strategy not found"}
        
        return {
            "success": True,
            "strategy_id": strategy.id,
            "name": strategy.name,
            "enabled": strategy.enabled,
            "message": f"Strategy '{strategy.name}' updated."
        }


async def approve_strategy_impl(strategy_id: str, context: AgentContext) -> dict:
    """
    Approve a strategy for live execution.
    """
    async with get_db_session() as db:
        strategy = await crud.approve_strategy(db, strategy_id, context.user_id)
        
        if not strategy:
            return {"error": "Strategy not found"}
        
        return {
            "success": True,
            "strategy_id": strategy.id,
            "name": strategy.name,
            "approved": True,
            "message": f"Strategy '{strategy.name}' approved for live trading. You can now enable it."
        }


async def run_strategy_impl(params: RunStrategyParams, context: AgentContext) -> dict:
    """
    Manually run a strategy.
    """
    async with get_db_session() as db:
        strategy = await crud.get_strategy(db, params.strategy_id, context.user_id)
        
        if not strategy:
            return {"error": "Strategy not found"}
        
        # Check approval for live runs
        if not params.dry_run and not strategy.approved:
            return {
                "error": "Strategy must be approved before live execution",
                "needs_approval": True
            }
        
        trigger = "dry_run" if params.dry_run else "manual"
        execution = await execute_strategy(
            db=db,
            strategy=strategy,
            trigger=trigger,
            dry_run=params.dry_run
        )
        
        data = execution.data or {}
        
        return {
            "execution_id": str(execution.id),
            "status": execution.status,
            "dry_run": params.dry_run,
            "summary": data.get("summary"),
            "actions": data.get("actions", []),
            "logs": data.get("logs", []),
            "error": data.get("error"),
        }


async def delete_strategy_impl(strategy_id: str, context: AgentContext) -> dict:
    """
    Delete a strategy.
    """
    async with get_db_session() as db:
        # Get name first for message
        strategy = await crud.get_strategy(db, strategy_id, context.user_id)
        if not strategy:
            return {"error": "Strategy not found"}
        
        name = strategy.name
        success = await crud.delete_strategy(db, strategy_id, context.user_id)
        
        return {
            "success": success,
            "message": f"Strategy '{name}' deleted." if success else "Failed to delete strategy"
        }


# ============================================================================
# Helper to get files for deployment
# ============================================================================

def get_chat_files_for_strategy_impl(context: AgentContext) -> dict:
    """
    Get list of files in current chat that could be used for a strategy.
    
    Used by LLM to see what files are available before deploying.
    """
    from database import SessionLocal
    
    with SessionLocal() as db:
        files = list_chat_files(db, context.chat_id)
        
        # Filter to code files
        code_files = [
            {
                "id": f.id,
                "filename": f.filename,
                "type": f.file_type,
                "size": f.size_bytes,
            }
            for f in files
            if f.file_type in ("python", "text", "json", "csv")
        ]
        
        return {
            "files": code_files,
            "count": len(code_files),
            "message": f"Found {len(code_files)} files that can be used in a strategy."
        }
