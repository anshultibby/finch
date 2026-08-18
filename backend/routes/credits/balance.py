"""
Credit balance, history, pricing and admin grants.
"""
from utils.logger import get_logger
from fastapi import APIRouter, Depends, HTTPException, Request, Header
from core.database import get_db_session
from services.credits import CreditsService
from core.config import Config
from auth.dependencies import get_current_user_id, verify_user_access
from .schemas import AddCreditsRequest, CreditBalanceResponse, SetPlanRequest

logger = get_logger(__name__)

router = APIRouter()


@router.get("/balance/{user_id}", response_model=CreditBalanceResponse)
async def get_credit_balance(
    user_id: str,
    authenticated_user_id: str = Depends(get_current_user_id),
):
    """
    Get the current credit balance for a user.

    Args:
        user_id: User ID

    Returns:
        Credit balance and total credits used
    """
    await verify_user_access(user_id, authenticated_user_id)
    try:
        async with get_db_session() as db:
            from sqlalchemy import select
            from models.user import UserAccount

            result = await db.execute(
                select(
                    UserAccount.credits,
                    UserAccount.total_credits_used,
                    UserAccount.plan,
                    UserAccount.subscription_status,
                    UserAccount.cancel_at_period_end,
                    UserAccount.current_period_end,
                    UserAccount.subscription_provider,
                ).where(UserAccount.user_id == user_id)
            )
            row = result.first()

            if not row:
                # New users may not have a user_accounts row yet (created lazily
                # on first credit operation). Return the free-tier default rather
                # than 404 — a user should never see an error for their own balance.
                from services.credits import DEFAULT_NEW_USER_CREDITS
                return CreditBalanceResponse(
                    user_id=user_id,
                    credits=DEFAULT_NEW_USER_CREDITS,
                    total_credits_used=0,
                    plan="free",
                )

            period_end = row[5]
            return CreditBalanceResponse(
                user_id=user_id,
                credits=row[0],
                total_credits_used=row[1],
                plan=row[2] or "free",
                subscription_status=row[3],
                cancel_at_period_end=bool(row[4]),
                current_period_end=period_end.isoformat() if period_end else None,
                subscription_provider=row[6],
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get credit balance: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/{user_id}")
async def get_credit_history(
    user_id: str,
    limit: int = 50,
    authenticated_user_id: str = Depends(get_current_user_id),
):
    """
    Get credit transaction history for a user.

    Args:
        user_id: User ID
        limit: Maximum number of transactions to return (default: 50)

    Returns:
        List of credit transactions (most recent first)
    """
    await verify_user_access(user_id, authenticated_user_id)
    try:
        async with get_db_session() as db:
            transactions = await CreditsService.get_transaction_history(
                db=db,
                user_id=user_id,
                limit=limit
            )
            
            return {
                "user_id": user_id,
                "transactions": transactions,
                "count": len(transactions)
            }
    
    except Exception as e:
        logger.error(f"Failed to get credit history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/add")
async def add_credits(
    request: AddCreditsRequest,
    x_admin_secret: str = Header(...),
):
    """
    Add credits to a user's balance (admin only).
    Requires X-Admin-Secret header matching ADMIN_SECRET env var.

    Args:
        request: Request with user_id, credits, and description

    Returns:
        Updated credit balance
    """
    import hmac
    if not Config.ADMIN_SECRET or not hmac.compare_digest(x_admin_secret, Config.ADMIN_SECRET):
        raise HTTPException(status_code=403, detail="Forbidden")
    try:
        if request.credits <= 0:
            raise HTTPException(status_code=400, detail="Credits must be positive")
        
        async with get_db_session() as db:
            success = await CreditsService.add_credits(
                db=db,
                user_id=request.user_id,
                credits=request.credits,
                transaction_type="admin_adjustment",
                description=request.description
            )
            
            if not success:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Get updated balance
            new_balance = await CreditsService.get_user_credits(db, request.user_id)
            
            return {
                "success": True,
                "user_id": request.user_id,
                "credits_added": request.credits,
                "new_balance": new_balance,
                "message": request.description
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add credits: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/pricing")
async def get_pricing_info():
    """
    Get pricing information for different models.
    
    Returns information about credit costs and model pricing.
    """
    from services.credits import MODEL_PRICING, CREDITS_PER_DOLLAR, PREMIUM_MULTIPLIER
    
    return {
        "credits_per_dollar": CREDITS_PER_DOLLAR,
        "premium_multiplier": PREMIUM_MULTIPLIER,
        "info": "Credits are calculated based on actual token usage with a 20% premium. 1 credit = 1 cent ($0.01). 100 credits = $1 USD.",
        "model_pricing": {
            model: {
                "input_per_million": pricing["input"],
                "output_per_million": pricing["output"],
                "cache_read_per_million": pricing["cache_read"],
                "cache_write_per_million": pricing["cache_write"]
            }
            for model, pricing in MODEL_PRICING.items()
        },
        "example": {
            "scenario": "100K input tokens + 10K output tokens (Claude Sonnet 4.5)",
            "calculation": {
                "input_cost_usd": 0.3,
                "output_cost_usd": 0.15,
                "total_usd": 0.45,
                "with_premium_usd": 0.54,
                "credits_charged": 54
            }
        }
    }

@router.post("/admin/set-plan")
async def admin_set_plan(request: SetPlanRequest, x_admin_secret: str = Header(...)):
    """
    Admin endpoint to manually set a user's plan.
    Requires X-Admin-Secret header matching ADMIN_SECRET env var.
    """
    import hmac
    if not Config.ADMIN_SECRET or not hmac.compare_digest(x_admin_secret, Config.ADMIN_SECRET):
        raise HTTPException(status_code=403, detail="Forbidden")

    if request.plan not in ("free", "pro", "admin"):
        raise HTTPException(status_code=400, detail="plan must be free, pro, or admin")

    async with get_db_session() as db:
        ok = await CreditsService.set_user_plan(db, request.user_id, request.plan)
        if not ok:
            raise HTTPException(status_code=404, detail="User not found")
        return {"success": True, "user_id": request.user_id, "plan": request.plan}
