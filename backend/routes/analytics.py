"""
Analytics API routes
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc as sa_desc
from services.analytics import analytics_service
from services.transaction_sync import transaction_sync_service
from crud.snaptrade_user import get_user_by_id as get_snaptrade_user
from core.database import get_async_db
from auth.dependencies import get_current_user_id, verify_user_access

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.post("/transactions/sync")
async def sync_transactions(
    user_id: str = Query(..., description="User ID (from Supabase auth)"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    force_resync: bool = Query(False),
    authenticated_user_id: str = Depends(get_current_user_id),
):
    """
    Sync transactions from connected brokerage
    
    Args:
        start_date: Start date in YYYY-MM-DD format (default: 1 year ago)
        end_date: End date in YYYY-MM-DD format (default: today)
        force_resync: Force re-sync even if recently synced
    """
    await verify_user_access(user_id, authenticated_user_id)
    try:
        # Parse dates if provided
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None
        
        result = await transaction_sync_service.sync_user_transactions(
            user_id=user_id,
            start_date=start_dt,
            end_date=end_dt,
            force_resync=force_resync
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance")
async def get_performance(
    user_id: str = Query(..., description="User ID (from Supabase auth)"),
    period: str = Query("all_time", regex="^(all_time|ytd|1m|3m|6m|1y)$"),
    authenticated_user_id: str = Depends(get_current_user_id),
):
    await verify_user_access(user_id, authenticated_user_id)
    try:
        metrics = analytics_service.calculate_performance_metrics(user_id, period)
        return metrics
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/patterns")
async def get_trading_patterns(
    user_id: str = Query(..., description="User ID (from Supabase auth)"),
    authenticated_user_id: str = Depends(get_current_user_id),
):
    await verify_user_access(user_id, authenticated_user_id)
    try:
        patterns = analytics_service.analyze_trading_patterns(user_id)
        return {"patterns": patterns}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transactions")
async def get_transactions(
    user_id: str = Query(..., description="User ID (from Supabase auth)"),
    symbol: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_async_db),
    authenticated_user_id: str = Depends(get_current_user_id),
):
    """
    Get transaction history

    Args:
        symbol: Filter by symbol (optional)
        start_date: Start date in YYYY-MM-DD format (optional)
        end_date: End date in YYYY-MM-DD format (optional)
        limit: Max results (default 100, max 500)
    """
    from models.brokerage import Transaction

    await verify_user_access(user_id, authenticated_user_id)
    try:
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None

        q = select(Transaction).where(Transaction.user_id == user_id)
        if symbol:
            q = q.where(Transaction.symbol == symbol.upper())
        if start_dt:
            q = q.where(Transaction.transaction_date >= start_dt)
        if end_dt:
            q = q.where(Transaction.transaction_date <= end_dt)
        q = q.order_by(sa_desc(Transaction.transaction_date)).limit(limit)

        result = await db.execute(q)
        transactions = result.scalars().all()

        formatted = [
            {
                "id": str(tx.id),
                "symbol": tx.symbol,
                "type": tx.transaction_type,
                "date": tx.transaction_date.isoformat(),
                "account_id": tx.account_id,
                "data": tx.data,
                "created_at": tx.created_at.isoformat()
            }
            for tx in transactions
        ]

        return {"transactions": formatted, "count": len(formatted)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

