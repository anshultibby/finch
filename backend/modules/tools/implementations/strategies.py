"""
Strategy tool implementations for the LLM agent.

These allow the LLM to deploy, inspect, update, and run strategies.
Files are now written to the strategy_files table (not ChatFiles).
"""
from typing import Optional, List
import json
import logging

from pydantic import BaseModel, Field
from sqlalchemy import select

from database import get_db_session
from modules.agent.context import AgentContext
from crud import strategies as crud
from models.db import ChatFile
from models.strategies import (
    CreateStrategyRequest,
    UpdateStrategyRequest,
    RiskLimits,
    CapitalConfig,
    StrategyInfoForLLM,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Pydantic models for tool parameters
# ============================================================================

class DeployStrategyParams(BaseModel):
    """Parameters for deploy_strategy tool.

    The LLM provides the file IDs of strategy.py and config.json from the
    current chat, and we promote them to a standalone strategy.
    """
    name: str = Field(..., description="Human-readable strategy name")
    description: str = Field(..., description="Plain-language description of what the strategy does")
    file_ids: List[str] = Field(
        ...,
        description="ChatFile IDs to promote — must include strategy.py and config.json",
    )
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
    Promote chat files into a first-class strategy.

    Reads the content of the specified ChatFiles, writes them to the
    strategy_files table (owned by the strategy, not the chat), then
    creates the Strategy DB record.
    """
    async with get_db_session() as db:
        # Load content from chat files
        result = await db.execute(
            select(ChatFile).where(ChatFile.id.in_(params.file_ids))
        )
        chat_files = {f.filename: f.content for f in result.scalars().all() if f.content}

        if "strategy.py" not in chat_files:
            return {
                "success": False,
                "error": "strategy.py not found in provided file_ids. Write strategy.py first.",
            }

        # Validate strategy.py contract
        strategy_code = chat_files["strategy.py"]
        if "async def run(ctx)" not in strategy_code:
            return {
                "success": False,
                "error": (
                    "strategy.py must define `async def run(ctx)` at the top level. "
                    "Do not use classes, decorators, or a synchronous def. "
                    "Example: async def run(ctx):\\n    ctx.log('tick')\\n    portfolio = ctx.kalshi.get_portfolio()"
                ),
            }

        # Parse config.json if present
        config_data: dict = {}
        if "config.json" in chat_files:
            try:
                config_data = json.loads(chat_files["config.json"])
            except json.JSONDecodeError:
                return {"success": False, "error": "config.json is not valid JSON"}

        platform = config_data.get("platform")
        if not platform or platform not in ("kalshi", "alpaca"):
            return {
                "success": False,
                "error": "config.json must specify 'platform': 'kalshi' or 'alpaca'",
            }

        # Validate capital field names — catch common wrong names upfront
        capital_data = config_data.get("capital", {})
        wrong_capital_keys = set(capital_data.keys()) - {"total", "per_trade", "max_positions"}
        if wrong_capital_keys:
            return {
                "success": False,
                "error": (
                    f"config.json capital has unrecognised fields: {sorted(wrong_capital_keys)}. "
                    "Required fields are: total, per_trade, max_positions. "
                    "Example: {\"total\": 1000, \"per_trade\": 50, \"max_positions\": 10}"
                ),
            }

        capital = None
        if capital_data:
            try:
                capital = CapitalConfig(**capital_data)
            except Exception as exc:
                return {"success": False, "error": f"config.json capital is invalid: {exc}"}

        risk_limits = None
        rl_data = config_data.get("risk_limits", {})
        if params.max_order_usd is not None:
            rl_data["max_order_usd"] = params.max_order_usd
        if params.max_daily_usd is not None:
            rl_data["max_daily_usd"] = params.max_daily_usd
        if rl_data:
            risk_limits = RiskLimits(**rl_data)

        request = CreateStrategyRequest(
            name=params.name,
            description=params.description,
            platform=platform,
            thesis=config_data.get("thesis", ""),
            schedule=params.schedule or config_data.get("schedule"),
            schedule_description=params.schedule_description or config_data.get("schedule_description"),
            capital=capital,
            risk_limits=risk_limits,
            source_chat_id=context.chat_id,
            files=chat_files,
        )

        strategy = await crud.create_strategy(db, context.user_id, request)

        return {
            "success": True,
            "strategy_id": strategy.id,
            "name": strategy.name,
            "platform": platform,
            "files": list(chat_files.keys()),
            "needs_approval": True,
            "message": (
                f"Strategy '{strategy.name}' created. "
                "It requires approval before live trading."
            ),
        }


async def list_strategies_impl(context: AgentContext) -> dict:
    async with get_db_session() as db:
        strategies = await crud.list_strategies(db, context.user_id)

        if not strategies:
            return {
                "strategies": [],
                "message": "No strategies found. Describe what you want to automate and I'll build it.",
            }

        strategy_list = [StrategyInfoForLLM.from_strategy(s).model_dump() for s in strategies]
        return {"strategies": strategy_list, "count": len(strategy_list)}


async def get_strategy_impl(strategy_id: str, context: AgentContext) -> dict:
    async with get_db_session() as db:
        strategy = await crud.get_strategy(db, strategy_id, context.user_id)
        if not strategy:
            return {"error": "Strategy not found"}

        config = strategy.config or {}
        stats = strategy.stats or {}

        executions = await crud.list_executions(db, strategy_id, limit=5)
        recent_runs = [
            {
                "time": ex.started_at.isoformat(),
                "status": ex.status,
                "trigger": (ex.data or {}).get("trigger"),
                "summary": (ex.data or {}).get("summary"),
            }
            for ex in executions
        ]

        # Load file list (names only, not content, to keep response small)
        files = await crud.get_strategy_files(db, strategy_id)

        return {
            "id": strategy.id,
            "name": strategy.name,
            "description": config.get("description", ""),
            "platform": config.get("platform", ""),
            "enabled": strategy.enabled,
            "approved": strategy.approved,
            "schedule": config.get("schedule_description"),
            "files": [f.filename for f in files],
            "stats": {
                "total_runs": stats.get("total_runs", 0),
                "successful_runs": stats.get("successful_runs", 0),
                "last_run": stats.get("last_run_summary"),
            },
            "recent_runs": recent_runs,
            "risk_limits": config.get("risk_limits"),
        }


async def update_strategy_impl(params: UpdateStrategyParams, context: AgentContext) -> dict:
    async with get_db_session() as db:
        risk_limits = None
        if params.max_order_usd is not None or params.max_daily_usd is not None:
            strategy = await crud.get_strategy(db, params.strategy_id, context.user_id)
            if not strategy:
                return {"error": "Strategy not found"}
            existing_rl = (strategy.config or {}).get("risk_limits", {})
            risk_limits = RiskLimits(
                max_order_usd=params.max_order_usd if params.max_order_usd is not None else existing_rl.get("max_order_usd"),
                max_daily_usd=params.max_daily_usd if params.max_daily_usd is not None else existing_rl.get("max_daily_usd"),
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
            "message": f"Strategy '{strategy.name}' updated.",
        }


async def approve_strategy_impl(strategy_id: str, context: AgentContext) -> dict:
    async with get_db_session() as db:
        strategy = await crud.approve_strategy(db, strategy_id, context.user_id)
        if not strategy:
            return {"error": "Strategy not found"}
        return {
            "success": True,
            "strategy_id": strategy.id,
            "name": strategy.name,
            "approved": True,
            "message": f"Strategy '{strategy.name}' approved. You can now enable it.",
        }


async def run_strategy_impl(params: RunStrategyParams, context: AgentContext) -> dict:
    async with get_db_session() as db:
        strategy = await crud.get_strategy(db, params.strategy_id, context.user_id)
        if not strategy:
            return {"error": "Strategy not found"}

        if not params.dry_run and not strategy.approved:
            return {
                "error": "Strategy must be approved before live execution",
                "needs_approval": True,
            }

        from modules.strategies.executor import execute_strategy
        trigger = "dry_run" if params.dry_run else "manual"
        execution = await execute_strategy(
            db=db,
            strategy=strategy,
            trigger=trigger,
            dry_run=params.dry_run,
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
    async with get_db_session() as db:
        strategy = await crud.get_strategy(db, strategy_id, context.user_id)
        if not strategy:
            return {"error": "Strategy not found"}
        name = strategy.name
        success = await crud.delete_strategy(db, strategy_id, context.user_id)
        return {
            "success": success,
            "message": f"Strategy '{name}' deleted." if success else "Failed to delete strategy",
        }


async def get_strategy_code_impl(strategy_id: str, context: AgentContext) -> dict:
    """Return the full code of a strategy's files."""
    async with get_db_session() as db:
        strategy = await crud.get_strategy(db, strategy_id, context.user_id)
        if not strategy:
            return {"error": "Strategy not found"}
        files = await crud.load_strategy_files(db, strategy)
        return {
            "strategy_id": strategy_id,
            "name": strategy.name,
            "files": files,
        }
