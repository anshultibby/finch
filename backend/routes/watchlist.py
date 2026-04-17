"""
API routes for user stock watchlist management
"""
import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, delete, text
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_async_db
from auth.dependencies import get_current_user_id, verify_user_access
from models.brokerage import UserWatchlist

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


class AddSymbolRequest(BaseModel):
    symbol: str


@router.get("/{user_id}")
async def get_watchlist(
    user_id: str,
    db: AsyncSession = Depends(get_async_db),
    authenticated_user_id: str = Depends(get_current_user_id),
):
    """Return watchlist items with current quote data."""
    await verify_user_access(user_id, authenticated_user_id)

    try:
        result = await db.execute(
            select(UserWatchlist).where(UserWatchlist.user_id == user_id).order_by(UserWatchlist.added_at)
        )
        items = result.scalars().all()

        if not items:
            return {"symbols": []}

        symbols_str = ",".join(item.symbol for item in items)
        added_at_map = {item.symbol: item.added_at.isoformat() if item.added_at else None for item in items}

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
    """Add a symbol to the user's watchlist."""
    await verify_user_access(user_id, authenticated_user_id)

    symbol = request.symbol.strip().upper()
    if not symbol:
        raise HTTPException(status_code=400, detail="Symbol is required")

    try:
        await db.execute(
            text(
                "INSERT INTO user_watchlist (id, user_id, symbol) "
                "VALUES (gen_random_uuid(), :user_id, :symbol) "
                "ON CONFLICT (user_id, symbol) DO NOTHING"
            ),
            {"user_id": user_id, "symbol": symbol},
        )
        await db.commit()
        return {"success": True, "symbol": symbol}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding {symbol} to watchlist for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to add to watchlist")


@router.delete("/{user_id}/{symbol}")
async def remove_from_watchlist(
    user_id: str,
    symbol: str,
    db: AsyncSession = Depends(get_async_db),
    authenticated_user_id: str = Depends(get_current_user_id),
):
    """Remove a symbol from the user's watchlist."""
    await verify_user_access(user_id, authenticated_user_id)

    try:
        await db.execute(
            delete(UserWatchlist).where(
                UserWatchlist.user_id == user_id,
                UserWatchlist.symbol == symbol.upper(),
            )
        )
        await db.commit()
        return {"success": True}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing {symbol} from watchlist for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove from watchlist")
