"""
Strategy / playbook library API (pillar 5, Phase-0).

Browse starter playbooks + the user's own, author/distill new ones, and adopt one
(persist it + bind it to the user's goal so the agent's <mission> runs it). The
starter catalog is code constants; only user-owned strategies are persisted.

Auth: trust the JWT (get_current_user_id) — ignore any client-supplied user_id.
"""
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from auth.dependencies import get_current_user_id
from core.database import get_async_db
from crud import strategies as crud_strategies
from crud.user_goals import get_goal, set_goal
from services.strategy_starters import STARTER_STRATEGIES, get_starter
from models.strategy import Strategy
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/strategies", tags=["strategies"])


def _to_dict(s: Strategy) -> dict:
    return {
        "id": s.id,
        "name": s.name,
        "slug": s.slug,
        "description": s.description,
        "style": s.style,
        "spec": s.spec,
        "source": s.source,
        "status": s.status,
        "source_id": s.source_id,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }


def _watchlist_from_spec(spec: Optional[dict]) -> list:
    uni = (spec or {}).get("universe") or {}
    return uni.get("explicit_watchlist") or uni.get("example_tickers") or []


class StrategyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    spec: Dict[str, Any]
    style: str = Field("custom", max_length=32)
    description: Optional[str] = Field(None, max_length=2000)
    source: str = Field("custom", max_length=32)  # custom | reddit


class AdoptRequest(BaseModel):
    """Adopt a starter (by slug) OR a distilled/custom spec. One of the two."""
    starter_slug: Optional[str] = Field(None, max_length=80)
    spec: Optional[Dict[str, Any]] = None
    name: Optional[str] = Field(None, max_length=120)
    style: Optional[str] = Field(None, max_length=32)
    description: Optional[str] = Field(None, max_length=2000)
    source: str = Field("custom", max_length=32)


@router.get("")
async def list_strategies(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    """The browse menu: starter playbooks + the user's adopted/authored ones."""
    mine = await crud_strategies.list_user_strategies(db, user_id)
    return {"starters": STARTER_STRATEGIES, "mine": [_to_dict(s) for s in mine]}


@router.get("/{strategy_id}")
async def get_one(
    strategy_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    row = await crud_strategies.get_strategy(db, strategy_id, user_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return _to_dict(row)


@router.post("")
async def create_strategy(
    body: StrategyCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    """Author/save a strategy (e.g. a distilled spec) without adopting it yet."""
    row = await crud_strategies.create_strategy(db, user_id, {
        "name": body.name, "spec": body.spec, "style": body.style,
        "description": body.description, "source": body.source, "status": "adopted",
    })
    return _to_dict(row)


@router.post("/adopt")
async def adopt_strategy(
    body: AdoptRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    """Persist a strategy for the user AND bind it to their goal so the agent runs it."""
    if body.starter_slug:
        starter = get_starter(body.starter_slug)
        if not starter:
            raise HTTPException(status_code=404, detail="Unknown starter strategy")
        data = {
            "name": starter["name"], "spec": starter["spec"], "style": starter["style"],
            "description": starter.get("description"), "source": "starter",
            "source_id": starter["slug"], "status": "adopted",
        }
    elif body.spec:
        data = {
            "name": body.name or (body.spec.get("name") if isinstance(body.spec, dict) else None) or "My strategy",
            "spec": body.spec, "style": body.style or "custom",
            "description": body.description, "source": body.source, "status": "adopted",
        }
    else:
        raise HTTPException(status_code=422, detail="Provide starter_slug or spec")

    row = await crud_strategies.create_strategy(db, user_id, data)

    # Bind to the goal (merge into config.strategy — never clobber other config).
    try:
        goal = await get_goal(db, user_id)
        config = dict(getattr(goal, "config", None) or {}) if goal else {}
        config["strategy"] = {
            "id": row.id, "name": row.name, "slug": row.slug, "style": row.style,
            "watchlist": _watchlist_from_spec(row.spec),
        }
        await set_goal(db, user_id, {"config": config})
    except Exception:
        logger.exception("adopt_strategy: goal binding failed for %s", user_id)

    return {"strategy": _to_dict(row), "bound_to_goal": True}
