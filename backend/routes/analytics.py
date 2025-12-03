"""
Analytics API routes
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from services.analytics import analytics_service
from services.transaction_sync import transaction_sync_service
from crud.snaptrade_user import get_user_by_id as get_snaptrade_user
from database import get_db

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.post("/transactions/sync")
async def sync_transactions(
    user_id: str = Query(..., description="User ID (from Supabase auth)"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    force_resync: bool = Query(False)
):
    """
    Sync transactions from connected brokerage
    
    Args:
        start_date: Start date in YYYY-MM-DD format (default: 1 year ago)
        end_date: End date in YYYY-MM-DD format (default: today)
        force_resync: Force re-sync even if recently synced
    """
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
    period: str = Query("all_time", regex="^(all_time|ytd|1m|3m|6m|1y)$")
):
    """
    Get portfolio performance metrics
    
    Args:
        period: Time period (all_time, ytd, 1m, 3m, 6m, 1y)
    """
    try:
        metrics = analytics_service.calculate_performance_metrics(user_id, period)
        return metrics
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/patterns")
async def get_trading_patterns(
    user_id: str = Query(..., description="User ID (from Supabase auth)")
):
    """Get behavioral trading patterns"""
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
    db: Session = Depends(get_db)
):
    """
    Get transaction history
    
    Args:
        symbol: Filter by symbol (optional)
        start_date: Start date in YYYY-MM-DD format (optional)
        end_date: End date in YYYY-MM-DD format (optional)
        limit: Max results (default 100, max 500)
    """
    from crud import transactions as tx_crud
    
    try:
        # Parse dates if provided
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None
        
        transactions = tx_crud.get_transactions(
            db,
            user_id=user_id,
            symbol=symbol,
            start_date=start_dt,
            end_date=end_dt,
            limit=limit
        )
        
        # Format response
        formatted = []
        for tx in transactions:
            formatted.append({
                "id": str(tx.id),
                "symbol": tx.symbol,
                "type": tx.transaction_type,
                "date": tx.transaction_date.isoformat(),
                "account_id": tx.account_id,
                "data": tx.data,
                "created_at": tx.created_at.isoformat()
            })
        
        return {
            "transactions": formatted,
            "count": len(formatted)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

