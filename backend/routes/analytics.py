"""
Analytics API routes
"""
import asyncio
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc as sa_desc
from services.transaction_sync import transaction_sync_service
from services.portfolio_analytics import analyze
from schemas.portfolio_analytics import AnalyzeRequest, AnalyticsView
from core.database import get_async_db
from auth.dependencies import get_current_user_id, verify_user_access
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def _pct(x: float) -> str:
    return f"{x * 100:.0f}%"


async def _narrate(view: AnalyticsView) -> Optional[str]:
    """One short, opinionated read of the portfolio — risk, concentration,
    redundancy, and what to consider. Numbers, not platitudes."""
    try:
        from litellm import acompletion
        from core.config import settings
        facts = {
            "total_value": round(view.total_value),
            "holdings": view.holding_count,
            "weighted_beta": view.weighted_beta,
            "top5_concentration": _pct(view.top5_concentration),
            "largest_position": _pct(view.largest_position_weight),
            "dividend_yield": _pct(view.dividend_yield),
            "annual_dividend_income": round(view.annual_dividend_income),
            "sectors": {a.label: _pct(a.weight) for a in view.sector_allocation[:6]},
            "top_holdings": {h.symbol: _pct(h.weight) for h in view.top_holdings[:6]},
        }
        sys = (
            "You are a sharp portfolio analyst. In 2-4 sentences, give the user the "
            "real read on their portfolio: concentration/risk (beta, top-5, single-name), "
            "sector tilt and what it implies, dividend income, and the single most useful "
            "thing to consider next. Be specific and cite the numbers. No disclaimers, no fluff."
        )
        import json as _json
        resp = await acompletion(
            model=settings.AGENT_LLM_MODEL,
            messages=[
                {"role": "system", "content": sys},
                {"role": "user", "content": _json.dumps(facts)},
            ],
            temperature=0.3,
            max_tokens=300,
        )
        return (resp.choices[0].message.content or "").strip() or None
    except Exception as e:
        logger.error(f"Portfolio narration failed: {e}")
        return None


@router.post("/portfolio", response_model=AnalyticsView)
async def analyze_portfolio(req: AnalyzeRequest):
    """Compute allocation, risk, concentration, and dividend metrics from the
    user's holdings, with an optional AI narration."""
    try:
        view = await asyncio.to_thread(analyze, req.holdings)
        if req.narrate and view.holding_count > 0:
            view.narration = await _narrate(view)
        return view
    except Exception as e:
        logger.error(f"Portfolio analytics failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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

