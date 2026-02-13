"""
Helpers to deploy strategies from code execution.

This module lets the LLM write strategy files to ChatFiles
and create a Strategy DB record in one call.
"""
from __future__ import annotations

from typing import Optional, Dict
import os
import asyncio
import json

from pydantic import BaseModel, Field

from database import get_db_session
from models.strategies import CreateStrategyRequest, RiskLimits
from modules.resource_manager import resource_manager
from crud import strategies as crud


class DeployStrategyFromFilesParams(BaseModel):
    """Parameters for deploying a strategy from raw file contents."""
    user_id: Optional[str] = Field(None, description="User ID (defaults to FINCH_USER_ID env)")
    chat_id: Optional[str] = Field(None, description="Chat ID where files should be saved (defaults to FINCH_CHAT_ID env)")
    name: str = Field(..., description="Strategy name")
    description: str = Field(..., description="Plain-language description")
    files: Dict[str, str] = Field(
        ...,
        description="Mapping of filename -> content (e.g., entry.py, exit.py, config.json)",
    )
    entrypoint: Optional[str] = Field(
        default=None,
        description="Entrypoint filename to execute (defaults to config or entry.py/strategy.py)",
    )
    schedule: Optional[str] = Field(None, description="Cron expression for scheduled runs")
    schedule_description: Optional[str] = Field(None, description="Human-readable schedule")
    max_order_usd: Optional[float] = Field(None, description="Max USD per order")
    max_daily_usd: Optional[float] = Field(None, description="Max USD per day")
    source_chat_id: Optional[str] = Field(None, description="Source chat where strategy was created")


async def _deploy_strategy_from_files_async(params: DeployStrategyFromFilesParams) -> dict:
    user_id = params.user_id or os.getenv("FINCH_USER_ID")
    chat_id = params.chat_id or os.getenv("FINCH_CHAT_ID")
    if not user_id or not chat_id:
        return {
            "success": False,
            "error": "Missing user_id/chat_id. Provide them or ensure FINCH_USER_ID/FINCH_CHAT_ID are set.",
        }

    file_ids: list[str] = []
    for filename, content in params.files.items():
        file_id = resource_manager.write_chat_file(
            user_id,
            chat_id,
            filename,
            content,
        )
        file_ids.append(file_id)

    resolved_entrypoint = params.entrypoint
    if not resolved_entrypoint:
        config_content = params.files.get("config.json")
        if config_content:
            try:
                config_data = json.loads(config_content)
                resolved_entrypoint = (
                    config_data.get("entrypoint")
                    or config_data.get("entry_script")
                )
            except json.JSONDecodeError:
                resolved_entrypoint = None
        if not resolved_entrypoint:
            if "strategy.py" in params.files:
                resolved_entrypoint = "strategy.py"
            elif "entry.py" in params.files:
                resolved_entrypoint = "entry.py"

    if not resolved_entrypoint:
        return {
            "success": False,
            "error": "Unable to determine entrypoint. Provide entrypoint or include strategy.py/entry.py.",
        }

    risk_limits = None
    if params.max_order_usd is not None or params.max_daily_usd is not None:
        risk_limits = RiskLimits(
            max_order_usd=params.max_order_usd,
            max_daily_usd=params.max_daily_usd,
        )

    request = CreateStrategyRequest(
        name=params.name,
        description=params.description,
        file_ids=file_ids,
        entrypoint=resolved_entrypoint,
        schedule=params.schedule,
        schedule_description=params.schedule_description,
        risk_limits=risk_limits,
        source_chat_id=params.source_chat_id or chat_id,
    )

    async with get_db_session() as db:
        strategy = await crud.create_strategy(db, user_id, request)

    return {
        "success": True,
        "strategy_id": strategy.id,
        "name": strategy.name,
        "entrypoint": resolved_entrypoint,
        "file_ids": file_ids,
        "message": f"Strategy '{strategy.name}' deployed.",
    }


def deploy_strategy_from_files(**kwargs) -> dict:
    """
    Sync wrapper for code execution environments.
    """
    params = DeployStrategyFromFilesParams(**kwargs)
    return asyncio.run(_deploy_strategy_from_files_async(params))


async def _inspect_strategy_async(strategy_id: str, user_id: Optional[str]) -> dict:
    async with get_db_session() as db:
        strategy = await crud.get_strategy(db, strategy_id, user_id)
        if not strategy and user_id is not None:
            strategy = await crud.get_strategy(db, strategy_id, None)

        if not strategy:
            return {"success": False, "error": "Strategy not found"}

        config = strategy.config or {}
        file_ids = config.get("file_ids", [])
        files = []
        if file_ids:
            from sqlalchemy import select
            from models.db import ChatFile

            result = await db.execute(
                select(ChatFile).where(ChatFile.id.in_(file_ids))
            )
            for file_obj in result.scalars().all():
                files.append({
                    "id": file_obj.id,
                    "filename": file_obj.filename,
                    "file_type": file_obj.file_type,
                    "chat_id": file_obj.chat_id,
                })

        return {
            "success": True,
            "strategy_id": strategy.id,
            "name": strategy.name,
            "user_id": strategy.user_id,
            "enabled": strategy.enabled,
            "approved": strategy.approved,
            "config": config,
            "files": files,
        }


def inspect_strategy(strategy_id: str, user_id: Optional[str] = None) -> dict:
    """
    Inspect a strategy and return ownership + file linkage.
    """
    resolved_user_id = user_id or os.getenv("FINCH_USER_ID")
    return asyncio.run(_inspect_strategy_async(strategy_id, resolved_user_id))


async def _claim_strategy_async(strategy_id: str, user_id: str, chat_id: Optional[str]) -> dict:
    async with get_db_session() as db:
        strategy = await crud.get_strategy(db, strategy_id, None)
        if not strategy:
            return {"success": False, "error": "Strategy not found"}

        strategy.user_id = user_id
        config = dict(strategy.config or {})
        if chat_id:
            config["source_chat_id"] = chat_id
        strategy.config = config
        await db.commit()
        await db.refresh(strategy)

        return {
            "success": True,
            "strategy_id": strategy.id,
            "user_id": strategy.user_id,
            "message": f"Strategy '{strategy.name}' claimed for user {user_id}.",
        }


def claim_strategy(strategy_id: str, user_id: Optional[str] = None, chat_id: Optional[str] = None) -> dict:
    """
    Reassign a strategy to the current user (useful if it was deployed
    with the wrong user_id).
    """
    resolved_user_id = user_id or os.getenv("FINCH_USER_ID")
    resolved_chat_id = chat_id or os.getenv("FINCH_CHAT_ID")
    if not resolved_user_id:
        return {"success": False, "error": "Missing user_id (set FINCH_USER_ID or pass explicitly)."}
    return asyncio.run(_claim_strategy_async(strategy_id, resolved_user_id, resolved_chat_id))
