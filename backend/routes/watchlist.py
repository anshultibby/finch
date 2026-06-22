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


class ScreenshotImportRequest(BaseModel):
    images: list[str]  # base64 data URLs (or raw base64) of watchlist screenshots
    list_id: Optional[str] = None


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


async def _ensure_named_list(user_id: str, name: str, db: AsyncSession) -> str:
    """Return the id of the user's list with this name, creating it if absent."""
    existing = await db.execute(
        text("SELECT id::text FROM watchlist_list WHERE user_id = :u AND name = :n"),
        {"u": user_id, "n": name},
    )
    row = existing.fetchone()
    if row:
        return row[0]
    next_pos = (await db.execute(
        text("SELECT COALESCE(MAX(position), -1) + 1 FROM watchlist_list WHERE user_id = :u"),
        {"u": user_id},
    )).scalar() or 0
    created = await db.execute(
        text(
            "INSERT INTO watchlist_list (id, user_id, name, list_type, position) "
            "VALUES (gen_random_uuid(), :u, :n, 'custom', :p) "
            "ON CONFLICT (user_id, name) DO UPDATE SET name = EXCLUDED.name "
            "RETURNING id::text"
        ),
        {"u": user_id, "n": name, "p": next_pos},
    )
    return created.fetchone()[0]


async def _resolve_target_list(user_id: str, list_id: Optional[str], db: AsyncSession) -> Optional[str]:
    """Use the given list_id, else fall back to the user's 'My Watchlist'."""
    if list_id:
        return list_id
    lists = await _ensure_default_lists(user_id, db)
    my_list = next((l for l in lists if l["list_type"] == "my_watchlist"), None)
    return my_list["id"] if my_list else None


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


async def _insert_symbols(user_id: str, list_id: str, symbols: list[str], source: str, db: AsyncSession) -> int:
    """Insert symbols into a list with the given source. Idempotent. Returns count attempted."""
    for symbol in symbols:
        await db.execute(
            text(
                "INSERT INTO user_watchlist (id, user_id, symbol, source, list_id) "
                "VALUES (gen_random_uuid(), :user_id, :symbol, :source, :list_id) "
                "ON CONFLICT (user_id, symbol, list_id) DO NOTHING"
            ),
            {"user_id": user_id, "symbol": symbol.upper(), "source": source, "list_id": list_id},
        )
    return len(symbols)


@router.post("/{user_id}/sync/robinhood")
async def sync_robinhood_watchlist(
    user_id: str,
    db: AsyncSession = Depends(get_async_db),
    authenticated_user_id: str = Depends(get_current_user_id),
):
    """Pull the user's Robinhood watchlists into a single 'Robinhood' list.

    Idempotent: replaces the previous robinhood-sourced entries each run so
    symbols removed on Robinhood drop off here too (manually-added symbols in the
    same list are left untouched)."""
    await verify_user_access(user_id, authenticated_user_id)

    from services import robinhood_auth
    if not await robinhood_auth.is_connected(user_id):
        raise HTTPException(status_code=400, detail="Robinhood is not connected")

    try:
        groups = await robinhood_auth.get_watchlist_symbols(user_id)
    except Exception as e:
        logger.error(f"Robinhood watchlist read failed for {user_id}: {e}")
        raise HTTPException(status_code=502, detail="Couldn't read your Robinhood watchlists")

    symbols = sorted({s for g in groups for s in g.get("symbols", [])})
    if not symbols:
        return {"success": True, "added": 0, "list_id": None, "list_name": "Robinhood",
                "message": "No watchlist symbols found on Robinhood"}

    try:
        list_id = await _ensure_named_list(user_id, "Robinhood", db)
        # Clear prior RH-sourced entries so removals propagate; keep manual ones.
        await db.execute(
            text("DELETE FROM user_watchlist WHERE user_id = :u AND list_id = :l AND source = 'robinhood'"),
            {"u": user_id, "l": list_id},
        )
        await _insert_symbols(user_id, list_id, symbols, "robinhood", db)
        await db.commit()
    except Exception as e:
        logger.error(f"Robinhood watchlist sync write failed for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to save synced watchlist")

    return {"success": True, "added": len(symbols), "list_id": list_id,
            "list_name": "Robinhood", "symbols": symbols}


@router.post("/{user_id}/sync/screenshot")
async def import_watchlist_screenshot(
    user_id: str,
    request: ScreenshotImportRequest,
    db: AsyncSession = Depends(get_async_db),
    authenticated_user_id: str = Depends(get_current_user_id),
):
    """Extract tickers from uploaded watchlist screenshots and add them to a list."""
    await verify_user_access(user_id, authenticated_user_id)

    if not request.images:
        raise HTTPException(status_code=400, detail="No images provided")

    from services.watchlist_import import extract_and_resolve
    try:
        resolved, unresolved = await extract_and_resolve(request.images)
    except Exception as e:
        logger.error(f"Screenshot watchlist import failed for {user_id}: {e}")
        raise HTTPException(status_code=502, detail="Couldn't read the screenshot")

    if not resolved:
        return {"success": True, "added": 0, "symbols": [], "unresolved": unresolved,
                "message": "No tickers found in the screenshot"}

    try:
        target_list_id = await _resolve_target_list(user_id, request.list_id, db)
        await _insert_symbols(user_id, target_list_id, [r["symbol"] for r in resolved], "screenshot", db)
        await db.commit()
    except Exception as e:
        logger.error(f"Screenshot import write failed for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to save imported symbols")

    return {"success": True, "added": len(resolved), "symbols": resolved,
            "unresolved": unresolved, "list_id": target_list_id}
