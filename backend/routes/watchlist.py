"""
API routes for user stock watchlist management with multiple named lists
"""
import asyncio
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, delete, text, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_async_db
from auth.dependencies import get_current_user_id, verify_user_access
from models.brokerage import UserWatchlist, WatchlistList

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/watchlist", tags=["watchlist"])

DEFAULT_LISTS = [
    {"name": "AI Picks", "list_type": "ai_picks", "position": 0},
    {"name": "My Watchlist", "list_type": "my_watchlist", "position": 1},
]


class AddSymbolRequest(BaseModel):
    symbol: str
    list_id: Optional[str] = None


class CreateListRequest(BaseModel):
    name: str


class RenameListRequest(BaseModel):
    name: str


async def _ensure_default_lists(user_id: str, db: AsyncSession) -> list[dict]:
    """Create default lists if they don't exist, return all lists."""
    result = await db.execute(
        select(WatchlistList).where(WatchlistList.user_id == user_id).order_by(WatchlistList.position)
    )
    existing = result.scalars().all()

    if existing:
        return [{"id": str(l.id), "name": l.name, "list_type": l.list_type, "position": l.position} for l in existing]

    created = []
    for dl in DEFAULT_LISTS:
        await db.execute(
            text(
                "INSERT INTO watchlist_list (id, user_id, name, list_type, position) "
                "VALUES (gen_random_uuid(), :user_id, :name, :list_type, :position) "
                "ON CONFLICT (user_id, name) DO NOTHING"
            ),
            {"user_id": user_id, **dl},
        )
    await db.commit()

    result = await db.execute(
        select(WatchlistList).where(WatchlistList.user_id == user_id).order_by(WatchlistList.position)
    )
    for l in result.scalars().all():
        created.append({"id": str(l.id), "name": l.name, "list_type": l.list_type, "position": l.position})
    return created


@router.get("/{user_id}/lists")
async def get_watchlist_lists(
    user_id: str,
    db: AsyncSession = Depends(get_async_db),
    authenticated_user_id: str = Depends(get_current_user_id),
):
    """Return all watchlist lists for the user with item counts."""
    await verify_user_access(user_id, authenticated_user_id)
    try:
        lists = await _ensure_default_lists(user_id, db)

        counts_result = await db.execute(
            text(
                "SELECT list_id::text, count(*) FROM user_watchlist "
                "WHERE user_id = :user_id AND list_id IS NOT NULL GROUP BY list_id"
            ),
            {"user_id": user_id},
        )
        count_map = {str(row[0]): row[1] for row in counts_result}

        for l in lists:
            l["item_count"] = count_map.get(l["id"], 0)

        return {"lists": lists}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching watchlist lists for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch lists")


@router.post("/{user_id}/lists")
async def create_watchlist_list(
    user_id: str,
    request: CreateListRequest,
    db: AsyncSession = Depends(get_async_db),
    authenticated_user_id: str = Depends(get_current_user_id),
):
    """Create a new custom watchlist list."""
    await verify_user_access(user_id, authenticated_user_id)

    name = request.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    if len(name) > 100:
        raise HTTPException(status_code=400, detail="Name too long")

    try:
        max_pos = await db.execute(
            text("SELECT COALESCE(MAX(position), -1) FROM watchlist_list WHERE user_id = :user_id"),
            {"user_id": user_id},
        )
        next_pos = (max_pos.scalar() or 0) + 1

        result = await db.execute(
            text(
                "INSERT INTO watchlist_list (id, user_id, name, list_type, position) "
                "VALUES (gen_random_uuid(), :user_id, :name, 'custom', :position) "
                "RETURNING id::text, name, list_type, position"
            ),
            {"user_id": user_id, "name": name, "position": next_pos},
        )
        row = result.fetchone()
        await db.commit()
        return {"success": True, "list": {"id": row[0], "name": row[1], "list_type": row[2], "position": row[3], "item_count": 0}}
    except Exception as e:
        if "uq_watchlist_list_user_name" in str(e):
            raise HTTPException(status_code=409, detail="A list with that name already exists")
        logger.error(f"Error creating watchlist list for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to create list")


@router.patch("/{user_id}/lists/{list_id}")
async def rename_watchlist_list(
    user_id: str,
    list_id: str,
    request: RenameListRequest,
    db: AsyncSession = Depends(get_async_db),
    authenticated_user_id: str = Depends(get_current_user_id),
):
    """Rename a watchlist list (custom lists only)."""
    await verify_user_access(user_id, authenticated_user_id)

    name = request.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")

    try:
        result = await db.execute(
            text("SELECT list_type FROM watchlist_list WHERE id = :id AND user_id = :user_id"),
            {"id": list_id, "user_id": user_id},
        )
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="List not found")
        if row[0] != "custom":
            raise HTTPException(status_code=400, detail="Cannot rename default lists")

        await db.execute(
            text("UPDATE watchlist_list SET name = :name WHERE id = :id AND user_id = :user_id"),
            {"name": name, "id": list_id, "user_id": user_id},
        )
        await db.commit()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error renaming watchlist list: {e}")
        raise HTTPException(status_code=500, detail="Failed to rename list")


@router.delete("/{user_id}/lists/{list_id}")
async def delete_watchlist_list(
    user_id: str,
    list_id: str,
    db: AsyncSession = Depends(get_async_db),
    authenticated_user_id: str = Depends(get_current_user_id),
):
    """Delete a watchlist list (custom lists only). Items are cascade-deleted."""
    await verify_user_access(user_id, authenticated_user_id)

    try:
        result = await db.execute(
            text("SELECT list_type FROM watchlist_list WHERE id = :id AND user_id = :user_id"),
            {"id": list_id, "user_id": user_id},
        )
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="List not found")
        if row[0] != "custom":
            raise HTTPException(status_code=400, detail="Cannot delete default lists")

        await db.execute(
            text("DELETE FROM watchlist_list WHERE id = :id AND user_id = :user_id"),
            {"id": list_id, "user_id": user_id},
        )
        await db.commit()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting watchlist list: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete list")


@router.get("/{user_id}")
async def get_watchlist(
    user_id: str,
    list_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_async_db),
    authenticated_user_id: str = Depends(get_current_user_id),
):
    """Return watchlist items with current quote data, optionally filtered by list."""
    await verify_user_access(user_id, authenticated_user_id)

    try:
        query = select(UserWatchlist).where(UserWatchlist.user_id == user_id)
        if list_id:
            query = query.where(UserWatchlist.list_id == list_id)
        query = query.order_by(UserWatchlist.added_at)

        result = await db.execute(query)
        items = result.scalars().all()

        if not items:
            return {"symbols": []}

        symbols_str = ",".join(item.symbol for item in items)
        added_at_map = {item.symbol: item.added_at.isoformat() if item.added_at else None for item in items}
        source_map = {item.symbol: item.source for item in items}
        list_id_map = {item.symbol: str(item.list_id) if item.list_id else None for item in items}

        from skills.financial_modeling_prep.scripts.market.quote import get_quote_snapshot

        try:
            quotes = await asyncio.to_thread(get_quote_snapshot, symbols_str)
        except Exception:
            quotes = []

        quote_map = {}
        if isinstance(quotes, list):
            for q in quotes:
                quote_map[q.get("symbol", "").upper()] = q

        symbols_out = []
        for item in items:
            q = quote_map.get(item.symbol.upper(), {})
            symbols_out.append({
                "symbol": item.symbol,
                "name": q.get("name"),
                "price": q.get("price"),
                "change": q.get("change"),
                "changesPercentage": q.get("changesPercentage"),
                "source": source_map.get(item.symbol, "manual"),
                "list_id": list_id_map.get(item.symbol),
                "added_at": added_at_map.get(item.symbol),
            })

        return {"symbols": symbols_out}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching watchlist for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch watchlist")


@router.post("/{user_id}")
async def add_to_watchlist(
    user_id: str,
    request: AddSymbolRequest,
    db: AsyncSession = Depends(get_async_db),
    authenticated_user_id: str = Depends(get_current_user_id),
):
    """Add a symbol to the user's watchlist. Defaults to 'My Watchlist' list."""
    await verify_user_access(user_id, authenticated_user_id)

    symbol = request.symbol.strip().upper()
    if not symbol:
        raise HTTPException(status_code=400, detail="Symbol is required")

    try:
        target_list_id = request.list_id
        if not target_list_id:
            lists = await _ensure_default_lists(user_id, db)
            my_list = next((l for l in lists if l["list_type"] == "my_watchlist"), None)
            if my_list:
                target_list_id = my_list["id"]

        await db.execute(
            text(
                "INSERT INTO user_watchlist (id, user_id, symbol, list_id) "
                "VALUES (gen_random_uuid(), :user_id, :symbol, :list_id) "
                "ON CONFLICT (user_id, symbol, list_id) DO NOTHING"
            ),
            {"user_id": user_id, "symbol": symbol, "list_id": target_list_id},
        )
        await db.commit()
        return {"success": True, "symbol": symbol, "list_id": target_list_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding {symbol} to watchlist for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to add to watchlist")


@router.delete("/{user_id}/{symbol}")
async def remove_from_watchlist(
    user_id: str,
    symbol: str,
    list_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_async_db),
    authenticated_user_id: str = Depends(get_current_user_id),
):
    """Remove a symbol from the user's watchlist. If list_id given, only from that list."""
    await verify_user_access(user_id, authenticated_user_id)

    try:
        stmt = delete(UserWatchlist).where(
            UserWatchlist.user_id == user_id,
            UserWatchlist.symbol == symbol.upper(),
        )
        if list_id:
            stmt = stmt.where(UserWatchlist.list_id == list_id)

        await db.execute(stmt)
        await db.commit()
        return {"success": True}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing {symbol} from watchlist for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove from watchlist")
