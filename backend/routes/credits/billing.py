"""
Stripe checkout, top-ups and subscription lifecycle.
"""
from utils.logger import get_logger
from fastapi import APIRouter, Depends, HTTPException
from core.database import get_db_session
from services.credits import CreditsService
from core.config import Config
from auth.dependencies import get_current_user_id, verify_user_access
from .schemas import CheckoutRequest, SubscriptionActionRequest, TOPUP_OPTIONS, TopupRequest

logger = get_logger(__name__)

router = APIRouter()


@router.post("/checkout")
async def create_checkout_session(
    request: CheckoutRequest,
    authenticated_user_id: str = Depends(get_current_user_id),
):
    await verify_user_access(request.user_id, authenticated_user_id)
    import stripe

    if not Config.STRIPE_SECRET_KEY or not Config.STRIPE_PRO_PRICE_ID:
        raise HTTPException(status_code=500, detail="Stripe not configured")

    client = stripe.StripeClient(Config.STRIPE_SECRET_KEY)
    base_url = Config.FRONTEND_URL or "http://localhost:3000"
    try:
        session = client.v1.checkout.sessions.create({
            "mode": "subscription",
            "line_items": [{"price": Config.STRIPE_PRO_PRICE_ID, "quantity": 1}],
            "success_url": f"{base_url}?upgraded=true",
            "cancel_url": base_url,
            "client_reference_id": request.user_id,
        })
        return {"url": session.url}
    except Exception as e:
        logger.error(f"Stripe checkout error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/topup")
async def create_topup_session(
    request: TopupRequest,
    authenticated_user_id: str = Depends(get_current_user_id),
):
    await verify_user_access(request.user_id, authenticated_user_id)
    import stripe

    if not Config.STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe not configured")

    option = TOPUP_OPTIONS.get(request.amount_cents)
    if not option:
        raise HTTPException(status_code=400, detail="Invalid top-up amount")

    client = stripe.StripeClient(Config.STRIPE_SECRET_KEY)
    base_url = Config.FRONTEND_URL or "http://localhost:3000"
    try:
        session = client.v1.checkout.sessions.create({
            "mode": "payment",
            "line_items": [{
                "price_data": {
                    "currency": "usd",
                    "unit_amount": request.amount_cents,
                    "product_data": {"name": option["label"]},
                },
                "quantity": 1,
            }],
            "success_url": f"{base_url}?topup=success",
            "cancel_url": base_url,
            "client_reference_id": request.user_id,
            "metadata": {"topup_credits": str(option["credits"])},
        })
        return {"url": session.url}
    except Exception as e:
        logger.error(f"Stripe topup error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cancel-subscription")
async def cancel_subscription(
    request: SubscriptionActionRequest,
    authenticated_user_id: str = Depends(get_current_user_id),
):
    await verify_user_access(request.user_id, authenticated_user_id)
    import stripe

    if not Config.STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe not configured")

    async with get_db_session() as db:
        from sqlalchemy import select
        from models.user import UserAccount
        result = await db.execute(
            select(UserAccount.stripe_subscription_id)
            .where(UserAccount.user_id == request.user_id)
        )
        row = result.first()
        sub_id = row[0] if row else None

    if not sub_id:
        raise HTTPException(status_code=400, detail="No active subscription")

    client = stripe.StripeClient(Config.STRIPE_SECRET_KEY)
    try:
        sub = client.v1.subscriptions.update(sub_id, {"cancel_at_period_end": True})
        from datetime import datetime, timezone
        cancel_at = sub.cancel_at
        period_end = datetime.fromtimestamp(cancel_at, tz=timezone.utc) if cancel_at else None

        async with get_db_session() as db:
            await CreditsService.set_subscription_info(
                db, request.user_id,
                cancel_at_period_end=True,
                current_period_end=period_end,
            )
            end_str = period_end.strftime("%b %d, %Y") if period_end else "end of billing period"
            await CreditsService.add_credits(
                db, request.user_id, 0,
                transaction_type="subscription_cancelled",
                description=f"Pro subscription cancelled — active until {end_str}",
                metadata={"reason": request.reason} if request.reason else None,
            )

        return {
            "success": True,
            "current_period_end": period_end.isoformat() if period_end else None,
        }
    except Exception as e:
        logger.error(f"Stripe cancel error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/resubscribe")
async def resubscribe(
    request: SubscriptionActionRequest,
    authenticated_user_id: str = Depends(get_current_user_id),
):
    await verify_user_access(request.user_id, authenticated_user_id)
    import stripe

    if not Config.STRIPE_SECRET_KEY or not Config.STRIPE_PRO_PRICE_ID:
        raise HTTPException(status_code=500, detail="Stripe not configured")

    async with get_db_session() as db:
        from sqlalchemy import select
        from models.user import UserAccount
        result = await db.execute(
            select(UserAccount.stripe_subscription_id, UserAccount.subscription_status)
            .where(UserAccount.user_id == request.user_id)
        )
        row = result.first()
        sub_id = row[0] if row else None
        sub_status = row[1] if row else None

    client = stripe.StripeClient(Config.STRIPE_SECRET_KEY)

    if sub_id and sub_status == "active":
        try:
            sub = client.v1.subscriptions.update(sub_id, {"cancel_at_period_end": False})
            from datetime import datetime, timezone
            cancel_at = sub.cancel_at
            period_end = datetime.fromtimestamp(cancel_at, tz=timezone.utc) if cancel_at else None

            async with get_db_session() as db:
                await CreditsService.set_subscription_info(
                    db, request.user_id,
                    cancel_at_period_end=False,
                    current_period_end=period_end,
                )
            return {"success": True}
        except Exception as e:
            logger.warning(f"Could not undo cancellation, creating new checkout: {e}")

    base_url = Config.FRONTEND_URL or "http://localhost:3000"
    try:
        session = client.v1.checkout.sessions.create({
            "mode": "subscription",
            "line_items": [{"price": Config.STRIPE_PRO_PRICE_ID, "quantity": 1}],
            "success_url": f"{base_url}?upgraded=true",
            "cancel_url": base_url,
            "client_reference_id": request.user_id,
        })
        return {"success": True, "checkout_url": session.url}
    except Exception as e:
        logger.error(f"Stripe resubscribe checkout error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
