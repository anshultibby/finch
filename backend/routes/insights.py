"""
Insights API — instant AI intelligence surfaced directly in the UI (no chat needed).

- GET /insights/why/{symbol}            -> "why is this moving today?" (cached, shared)
- GET /insights/portfolio-digest/{uid}  -> generated "Today" story for the user's
                                           portfolio (or watchlist fallback)
"""
import logging

from fastapi import APIRouter, Depends, HTTPException

from auth.dependencies import get_current_user_id, verify_user_access

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("/why/{symbol}")
async def why_is_it_moving(
    symbol: str,
    authenticated_user_id: str = Depends(get_current_user_id),
):
    """Explain today's move for a symbol in 1-2 grounded sentences."""
    from services.move_explainer import explain_move

    try:
        return await explain_move(symbol)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"No quote found for {symbol.upper()}")
    except Exception:
        logger.exception("explain_move failed for %s", symbol)
        raise HTTPException(status_code=502, detail="Failed to generate explanation")


@router.get("/portfolio-digest/{user_id}")
async def portfolio_digest(
    user_id: str,
    authenticated_user_id: str = Depends(get_current_user_id),
):
    """Generated 'Today' narrative + top movers for the user's portfolio/watchlist."""
    await verify_user_access(user_id, authenticated_user_id)
    from services.portfolio_digest import get_portfolio_digest

    try:
        return await get_portfolio_digest(user_id)
    except Exception:
        logger.exception("portfolio digest failed for %s", user_id)
        raise HTTPException(status_code=502, detail="Failed to generate digest")
