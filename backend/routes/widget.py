"""
Widget routes. Authenticated CRUD + publish/clone + tile-data resolution, plus
two no-auth /shared/{slug} routes that back the public share page.

Auth: every route except /shared/* uses get_current_user_id and trusts the JWT
only — the finch_api sandbox client appends a `user_id` query param, which we
ignore. See docs/widgets/spec.md.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from auth.dependencies import get_current_user_id
from core.database import get_db_session
from crud import widget as crud
from models.widget import Widget
from schemas.widget import (
    CreateWidgetRequest,
    PublicWidgetResponse,
    PublishRequest,
    UpdateWidgetRequest,
    WidgetResponse,
    WidgetSpec,
    WidgetSummary,
)
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/widgets", tags=["widgets"])


# ──────────────────────────────────────────────────────────────────────────
# Serialization
# ──────────────────────────────────────────────────────────────────────────
def _share_url(w: Widget) -> Optional[str]:
    if w.visibility != "public" or not w.slug:
        return None
    from core.config import Config
    return f"{Config.FRONTEND_URL.rstrip('/')}/share/widget/{w.slug}"


def _to_response(w: Widget, viewer_id: str) -> WidgetResponse:
    return WidgetResponse(
        id=w.id,
        user_id=w.user_id,
        title=w.title,
        description=w.description,
        emoji=w.emoji,
        tags=w.tags,
        spec=w.spec,
        visibility=w.visibility,
        slug=w.slug,
        cloned_from=w.cloned_from,
        view_count=w.view_count,
        clone_count=w.clone_count,
        is_owner=(w.user_id == viewer_id),
        share_url=_share_url(w),
        created_at=w.created_at.isoformat(),
        updated_at=w.updated_at.isoformat(),
    )


def _to_summary(w: Widget) -> WidgetSummary:
    return WidgetSummary(
        id=w.id,
        title=w.title,
        description=w.description,
        emoji=w.emoji,
        tags=w.tags,
        visibility=w.visibility,
        slug=w.slug,
        view_count=w.view_count,
        clone_count=w.clone_count,
        created_at=w.created_at.isoformat(),
    )


def _ensure_goal_pin(spec: dict) -> dict:
    """Guarantee the cockpit keeps a goal block (agent may reorder, not remove)."""
    tiles = spec.get("tiles", [])
    if not any((t.get("query") or {}).get("source") == "goal" for t in tiles):
        goal_tile = {"id": "goal", "type": "goal", "size": "full", "query": {"source": "goal"}}
        spec = {**spec, "tiles": [goal_tile, *tiles]}
    return spec


async def _owned_or_404(db: AsyncSession, widget_id: str, user_id: str) -> Widget:
    w = await crud.get_widget(db, widget_id)
    if not w or w.user_id != user_id:
        # 404 (not 403) so private widgets are indistinguishable from missing.
        raise HTTPException(status_code=404, detail="Widget not found")
    return w


# ──────────────────────────────────────────────────────────────────────────
# Collection routes (order matters: /gallery before /{id})
# ──────────────────────────────────────────────────────────────────────────
@router.post("", response_model=WidgetResponse)
async def create_widget(body: CreateWidgetRequest, user_id: str = Depends(get_current_user_id)):
    if not body.spec.tile_ids_unique():
        raise HTTPException(status_code=422, detail="Tile ids must be unique within a widget")
    async with get_db_session() as db:
        w = await crud.create_widget(
            db, user_id,
            title=body.title, spec=body.spec, description=body.description,
            emoji=body.emoji, tags=body.tags,
        )
        return _to_response(w, user_id)


@router.get("", response_model=List[WidgetSummary])
async def list_widgets(user_id: str = Depends(get_current_user_id)):
    async with get_db_session() as db:
        return [_to_summary(w) for w in await crud.list_my_widgets(db, user_id)]


@router.get("/gallery", response_model=List[WidgetSummary])
async def gallery(
    q: Optional[str] = None,
    sort: str = Query("recent", pattern="^(recent|popular)$"),
    user_id: str = Depends(get_current_user_id),
):
    async with get_db_session() as db:
        return [_to_summary(w) for w in await crud.list_gallery(db, q=q, sort=sort)]


@router.get("/cockpit", response_model=WidgetResponse)
async def get_cockpit(user_id: str = Depends(get_current_user_id)):
    """The user's home board — get-or-create from the per-goal default template."""
    from services.cockpit_template import default_cockpit_spec
    from crud.user_goals import get_goal
    async with get_db_session() as db:
        w = await crud.get_cockpit(db, user_id)
        if w is None:
            goal = await get_goal(db, user_id)
            w = await crud.create_widget(
                db, user_id, title="Mission", spec=default_cockpit_spec(goal), kind="cockpit",
            )
        return _to_response(w, user_id)


@router.get("/{widget_id}", response_model=WidgetResponse)
async def get_widget(widget_id: str, user_id: str = Depends(get_current_user_id)):
    async with get_db_session() as db:
        w = await crud.get_widget(db, widget_id)
        if not w or (w.user_id != user_id and w.visibility != "public"):
            raise HTTPException(status_code=404, detail="Widget not found")
        return _to_response(w, user_id)


@router.patch("/{widget_id}", response_model=WidgetResponse)
async def update_widget(
    widget_id: str, body: UpdateWidgetRequest, user_id: str = Depends(get_current_user_id)
):
    updates = body.model_dump(exclude_none=True)
    if "spec" in updates:
        spec = body.spec
        if not spec.tile_ids_unique():
            raise HTTPException(status_code=422, detail="Tile ids must be unique within a widget")
        updates["spec"] = spec.model_dump(mode="json")
    async with get_db_session() as db:
        w = await _owned_or_404(db, widget_id, user_id)
        # The cockpit's goal block is pinned — the home can't be left goalless.
        if w.kind == "cockpit" and "spec" in updates:
            updates["spec"] = _ensure_goal_pin(updates["spec"])
        w = await crud.update_widget(db, w, updates)
        return _to_response(w, user_id)


@router.delete("/{widget_id}")
async def delete_widget(widget_id: str, user_id: str = Depends(get_current_user_id)):
    async with get_db_session() as db:
        w = await _owned_or_404(db, widget_id, user_id)
        await crud.delete_widget(db, w)
        return {"ok": True}


@router.post("/{widget_id}/publish", response_model=WidgetResponse)
async def publish_widget(
    widget_id: str, body: PublishRequest = PublishRequest(), user_id: str = Depends(get_current_user_id)
):
    async with get_db_session() as db:
        w = await _owned_or_404(db, widget_id, user_id)
        if body.unpublish:
            w = await crud.unpublish_widget(db, w)
        else:
            try:
                w = await crud.publish_widget(db, w)
            except crud.PublishError as e:
                raise HTTPException(status_code=422, detail=str(e))
        return _to_response(w, user_id)


@router.post("/{widget_id}/clone", response_model=WidgetResponse)
async def clone_widget(widget_id: str, user_id: str = Depends(get_current_user_id)):
    async with get_db_session() as db:
        source = await crud.get_widget(db, widget_id)
        if not source or (source.user_id != user_id and source.visibility != "public"):
            raise HTTPException(status_code=404, detail="Widget not found")
        clone = await crud.clone_widget(db, source, user_id)
        return _to_response(clone, user_id)


@router.get("/{widget_id}/data")
async def get_widget_data(
    widget_id: str,
    tile: Optional[str] = None,  # resolve just one tile → per-tile streaming
    user_id: str = Depends(get_current_user_id),
):
    async with get_db_session() as db:
        w = await crud.get_widget(db, widget_id)
        if not w or (w.user_id != user_id and w.visibility != "public"):
            raise HTTPException(status_code=404, detail="Widget not found")
    spec = w.spec
    if tile:
        spec = {**spec, "tiles": [t for t in (spec.get("tiles") or []) if t.get("id") == tile]}
    from services.widget_data import resolve_widget_data
    return await resolve_widget_data(spec, viewer_user_id=user_id)


# ──────────────────────────────────────────────────────────────────────────
# Public routes — no auth (pattern: routes/chat.py get_shared_chat)
# ──────────────────────────────────────────────────────────────────────────
@router.get("/shared/{slug}", response_model=PublicWidgetResponse)
async def get_shared_widget(slug: str):
    async with get_db_session() as db:
        w = await crud.get_widget_by_slug(db, slug)
        if not w:
            raise HTTPException(status_code=404, detail="Widget not found or not public")
        # Fire-and-forget view count; a failed increment must not break the read.
        try:
            await crud.increment_view_count(db, w.id)
        except Exception:
            logger.warning("widget view-count increment failed for %s", slug)
        return PublicWidgetResponse(
            id=w.id, slug=w.slug, title=w.title, description=w.description, emoji=w.emoji,
            tags=w.tags, spec=w.spec, view_count=w.view_count, clone_count=w.clone_count,
        )


@router.get("/shared/{slug}/data")
async def get_shared_widget_data(slug: str):
    async with get_db_session() as db:
        w = await crud.get_widget_by_slug(db, slug)
        if not w:
            raise HTTPException(status_code=404, detail="Widget not found or not public")
        spec = w.spec
    from services.widget_data import resolve_widget_data
    # viewer_user_id=None → personal-binding tiles render a "connect" empty state.
    return await resolve_widget_data(spec, viewer_user_id=None)
