"""
Deploy strategy from code execution environment.

This module is callable from inside the user's E2B sandbox so the LLM can
deploy a strategy after writing strategy.py + config.json there.

Files are stored in the strategy_files table (owned by the strategy),
not in ChatFiles.
"""
from __future__ import annotations

import asyncio
import json
import os
from typing import Optional, Dict

from pydantic import BaseModel, Field

from database import get_db_session
from models.strategies import (
    CreateStrategyRequest,
    CapitalConfig,
    RiskLimits,
)
from crud import strategies as crud


class DeployStrategyFromFilesParams(BaseModel):
    """Parameters for deploying a strategy from raw file contents."""
    user_id: Optional[str] = Field(None, description="User ID (defaults to FINCH_USER_ID env)")
    chat_id: Optional[str] = Field(None, description="Source chat ID (defaults to FINCH_CHAT_ID env)")
    name: str = Field(..., description="Strategy display name")
    description: str = Field(..., description="Plain-language description")
    files: Dict[str, str] = Field(
        ...,
        description="Mapping of filename -> content (must include strategy.py and config.json)",
    )
    # These can be extracted from config.json but can be overridden
    platform: Optional[str] = Field(None, description="'kalshi' or 'alpaca' (read from config.json if absent)")
    schedule: Optional[str] = Field(None, description="Cron expression")
    schedule_description: Optional[str] = Field(None, description="Human-readable schedule")


async def _deploy_async(params: DeployStrategyFromFilesParams) -> dict:
    user_id = params.user_id or os.getenv("FINCH_USER_ID")
    chat_id = params.chat_id or os.getenv("FINCH_CHAT_ID")

    if not user_id:
        return {
            "success": False,
            "error": "Missing user_id. Provide it or ensure FINCH_USER_ID env var is set.",
        }

    if "strategy.py" not in params.files:
        return {
            "success": False,
            "error": "files must include 'strategy.py'",
        }

    # Parse config.json if present
    config_data: dict = {}
    if "config.json" in params.files:
        try:
            config_data = json.loads(params.files["config.json"])
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"Invalid config.json: {e}"}

    platform = params.platform or config_data.get("platform")
    if not platform:
        return {
            "success": False,
            "error": "platform must be specified (in config.json or as a parameter)",
        }
    if platform not in ("kalshi", "alpaca"):
        return {"success": False, "error": f"Invalid platform '{platform}'"}

    # Build capital config if present in config.json
    capital = None
    if "capital" in config_data:
        try:
            capital = CapitalConfig(**config_data["capital"])
        except Exception:
            pass

    # Build risk limits
    risk_limits = None
    if "risk_limits" in config_data:
        try:
            risk_limits = RiskLimits(**config_data["risk_limits"])
        except Exception:
            pass

    request = CreateStrategyRequest(
        name=params.name,
        description=params.description,
        platform=platform,
        thesis=config_data.get("thesis", ""),
        schedule=params.schedule or config_data.get("schedule"),
        schedule_description=params.schedule_description or config_data.get("schedule_description"),
        capital=capital,
        risk_limits=risk_limits,
        source_chat_id=chat_id,
        files=params.files,
    )

    async with get_db_session() as db:
        strategy = await crud.create_strategy(db, user_id, request)

    return {
        "success": True,
        "strategy_id": strategy.id,
        "name": strategy.name,
        "platform": platform,
        "files": list(params.files.keys()),
        "message": (
            f"Strategy '{strategy.name}' deployed. "
            "It requires approval before live trading."
        ),
    }


def deploy_strategy_from_files(**kwargs) -> dict:
    """Sync wrapper — callable from code execution (asyncio.run)."""
    params = DeployStrategyFromFilesParams(**kwargs)
    return asyncio.run(_deploy_async(params))
