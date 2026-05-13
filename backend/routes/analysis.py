"""
API routes for AI-generated stock analysis notes
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_async_db
from auth.dependencies import get_current_user_id
from models.brokerage import StockAnalysis

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("")
async def list_analyses(
    db: AsyncSession = Depends(get_async_db),
    user_id: str = Depends(get_current_user_id),
):
    """List all stocks with analysis notes (powers Research section)."""
    try:
        result = await db.execute(
            select(
                StockAnalysis.symbol,
                sa_func.count(StockAnalysis.id).label("note_count"),
                sa_func.max(StockAnalysis.updated_at).label("latest_updated_at"),
            )
            .where(StockAnalysis.user_id == user_id)
            .group_by(StockAnalysis.symbol)
            .order_by(sa_func.max(StockAnalysis.updated_at).desc())
        )
        rows = result.all()
        return {
            "analyses": [
                {
                    "symbol": row.symbol,
                    "note_count": row.note_count,
                    "updated_at": row.latest_updated_at.isoformat() if row.latest_updated_at else None,
                }
                for row in rows
            ]
        }
    except Exception as e:
        logger.error(f"Error listing analyses for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to list analyses")


@router.get("/{symbol}")
async def get_analysis(
    symbol: str,
    db: AsyncSession = Depends(get_async_db),
    user_id: str = Depends(get_current_user_id),
):
    """Get all analysis notes for a specific stock, newest first."""
    try:
        result = await db.execute(
            select(StockAnalysis)
            .where(
                StockAnalysis.user_id == user_id,
                StockAnalysis.symbol == symbol.upper(),
            )
            .order_by(StockAnalysis.created_at.desc())
        )
        items = result.scalars().all()
        if not items:
            return {"found": False, "symbol": symbol.upper(), "notes": []}
        return {
            "found": True,
            "symbol": symbol.upper(),
            "notes": [
                {
                    "id": str(item.id),
                    "title": item.title,
                    "content": item.content,
                    "chat_id": str(item.chat_id) if item.chat_id else None,
                    "created_at": item.created_at.isoformat() if item.created_at else None,
                    "updated_at": item.updated_at.isoformat() if item.updated_at else None,
                }
                for item in items
            ],
        }
    except Exception as e:
        logger.error(f"Error fetching analysis for {symbol}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch analysis")
