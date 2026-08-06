"""
CRUD for widgets. Async free functions, owner-scoped reads/writes, plus the
public gallery + slug lookup. See docs/widgets/spec.md.
"""
import re
import secrets
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import String, select, update as sa_update, or_
from sqlalchemy.ext.asyncio import AsyncSession

from models.widget import Widget
from schemas.widget import WidgetSpec, PUBLIC_SAFE_SOURCES


def _new_id() -> str:
    return uuid.uuid4().hex


def _slugify(title: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", (title or "widget").lower()).strip("-")
    base = base[:40] or "widget"
    return f"{base}-{secrets.token_hex(2)}"  # 4 hex chars of entropy


class PublishError(ValueError):
    """Raised when a spec can't be safely published (unsafe data source)."""


def assert_publishable(spec: Dict[str, Any]) -> None:
    """Sweep the spec — every tile's data source must be public-safe.

    Personal sources (user_portfolio / user_watchlist) are allowed because they
    are symbolic: they carry no account ids (enforced by `extra='forbid'` on the
    query schema) and resolve per viewer. Anything outside the allow-list is
    rejected with a per-tile reason the caller can surface to the agent.
    """
    for tile in spec.get("tiles", []):
        queries = [tile.get("query")] if tile.get("query") else [
            part.get("query") for part in (tile.get("queries") or {}).values()
        ]
        for query in queries:
            if query is None:
                continue  # self-contained (e.g. a chart_spec with data baked in) — safe
            source = query.get("source")
            if source not in PUBLIC_SAFE_SOURCES:
                raise PublishError(
                    f"Tile '{tile.get('id')}' uses data source '{source}', which "
                    f"cannot be published publicly."
                )


async def create_widget(
    db: AsyncSession,
    user_id: str,
    *,
    title: str,
    spec: WidgetSpec,
    description: Optional[str] = None,
    emoji: Optional[str] = None,
    tags: Optional[List[str]] = None,
    cloned_from: Optional[str] = None,
) -> Widget:
    widget = Widget(
        id=_new_id(),
        user_id=user_id,
        title=title,
        description=description,
        emoji=emoji,
        tags=tags,
        spec=spec.model_dump(mode="json"),
        visibility="private",
        cloned_from=cloned_from,
    )
    db.add(widget)
    await db.commit()
    await db.refresh(widget)
    return widget


async def get_widget(db: AsyncSession, widget_id: str) -> Optional[Widget]:
    return (
        await db.execute(select(Widget).where(Widget.id == widget_id))
    ).scalar_one_or_none()


async def get_widget_by_slug(db: AsyncSession, slug: str) -> Optional[Widget]:
    return (
        await db.execute(
            select(Widget).where(Widget.slug == slug, Widget.visibility == "public")
        )
    ).scalar_one_or_none()


async def list_my_widgets(db: AsyncSession, user_id: str) -> List[Widget]:
    return list(
        (
            await db.execute(
                select(Widget)
                .where(Widget.user_id == user_id)
                .order_by(Widget.updated_at.desc())
            )
        ).scalars()
    )


async def list_gallery(
    db: AsyncSession,
    *,
    q: Optional[str] = None,
    sort: str = "recent",
    limit: int = 50,
) -> List[Widget]:
    stmt = select(Widget).where(Widget.visibility == "public")
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(
                Widget.title.ilike(like),
                Widget.description.ilike(like),
                Widget.tags.cast(String).ilike(like),
            )
        )
    if sort == "popular":
        stmt = stmt.order_by(Widget.clone_count.desc(), Widget.view_count.desc())
    else:
        stmt = stmt.order_by(Widget.created_at.desc())
    stmt = stmt.limit(min(limit, 100))
    return list((await db.execute(stmt)).scalars())


async def update_widget(
    db: AsyncSession, widget: Widget, updates: Dict[str, Any]
) -> Widget:
    for key, value in updates.items():
        setattr(widget, key, value)
    await db.commit()
    await db.refresh(widget)
    return widget


async def delete_widget(db: AsyncSession, widget: Widget) -> None:
    await db.delete(widget)
    await db.commit()


async def publish_widget(db: AsyncSession, widget: Widget) -> Widget:
    """Make public — mint a slug once and keep it stable across re-publishes so
    a shared URL never breaks."""
    assert_publishable(widget.spec)
    if not widget.slug:
        widget.slug = _slugify(widget.title)
    widget.visibility = "public"
    await db.commit()
    await db.refresh(widget)
    return widget


async def unpublish_widget(db: AsyncSession, widget: Widget) -> Widget:
    """Make private again. The slug is retained (not cleared) so re-publishing
    restores the same URL."""
    widget.visibility = "private"
    await db.commit()
    await db.refresh(widget)
    return widget


async def clone_widget(
    db: AsyncSession, source: Widget, user_id: str
) -> Widget:
    """Copy a widget's spec into the caller's collection. Symbolic bindings
    (user_portfolio/user_watchlist) automatically rebind to the cloner because
    they resolve per viewer — nothing to rewrite."""
    clone = Widget(
        id=_new_id(),
        user_id=user_id,
        title=source.title,
        description=source.description,
        emoji=source.emoji,
        tags=source.tags,
        spec=source.spec,
        visibility="private",
        cloned_from=source.id,
    )
    db.add(clone)
    await db.execute(
        sa_update(Widget)
        .where(Widget.id == source.id)
        .values(clone_count=Widget.clone_count + 1)
    )
    await db.commit()
    await db.refresh(clone)
    return clone


async def increment_view_count(db: AsyncSession, widget_id: str) -> None:
    await db.execute(
        sa_update(Widget)
        .where(Widget.id == widget_id)
        .values(view_count=Widget.view_count + 1)
    )
    await db.commit()
