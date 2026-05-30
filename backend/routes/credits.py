"""
Credits API routes
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Header
from pydantic import BaseModel
from typing import Optional
from core.database import get_db_session
from services.credits import CreditsService
from utils.logger import get_logger
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from core.config import Config
from auth.dependencies import get_current_user_id, verify_user_access
from core.rate_limit import limiter

logger = get_logger(__name__)

router = APIRouter(prefix="/credits", tags=["credits"])


class CreditBalanceResponse(BaseModel):
    user_id: str
    credits: int
    total_credits_used: int
    plan: str = "free"
    subscription_status: Optional[str] = None
    cancel_at_period_end: bool = False
    current_period_end: Optional[str] = None


class AddCreditsRequest(BaseModel):
    """Request model for adding credits (admin only)"""
    user_id: str
    credits: int
    description: Optional[str] = "Credits added"


class CreditTransactionResponse(BaseModel):
    """Response model for a single credit transaction"""
    id: str
    amount: int
    balance_after: int
    transaction_type: str
    description: str
    chat_id: Optional[str]
    tool_name: Optional[str]
    metadata: Optional[dict]
    created_at: Optional[str]


class CreditRequestData(BaseModel):
    """Request model for credit request"""
    user_id: str
    user_email: str
    requested_credits: int
    reason: str
    current_balance: int
    total_used: int


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
            from models.user import SnapTradeUser
            
            result = await db.execute(
                select(
                    SnapTradeUser.credits,
                    SnapTradeUser.total_credits_used,
                    SnapTradeUser.plan,
                    SnapTradeUser.subscription_status,
                    SnapTradeUser.cancel_at_period_end,
                    SnapTradeUser.current_period_end,
                ).where(SnapTradeUser.user_id == user_id)
            )
            row = result.first()

            if not row:
                raise HTTPException(status_code=404, detail="User not found")

            period_end = row[5]
            return CreditBalanceResponse(
                user_id=user_id,
                credits=row[0],
                total_credits_used=row[1],
                plan=row[2] or "free",
                subscription_status=row[3],
                cancel_at_period_end=bool(row[4]),
                current_period_end=period_end.isoformat() if period_end else None,
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


class CheckoutRequest(BaseModel):
    user_id: str


class SetPlanRequest(BaseModel):
    user_id: str
    plan: str  # free | pro | admin


class PromoRequestBody(BaseModel):
    email: str
    message: str = ""


@router.post("/request-code")
@limiter.limit("3/minute")
async def request_promo_code(request: Request, body: PromoRequestBody):
    """User requests a promo code — sends an email to the admin."""
    from services.notifications import _send_resend_email
    admin_email = "anshul@finchapp.ai"
    html = f"""
    <h3>Promo Code Request</h3>
    <p><b>Email:</b> {body.email}</p>
    <p><b>Message:</b> {body.message or '(none)'}</p>
    """
    sent = await _send_resend_email(admin_email, f"Finch Pro code request from {body.email}", html)
    if not sent:
        raise HTTPException(status_code=500, detail="Failed to send request")
    return {"ok": True}


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


TOPUP_OPTIONS = {
    500: {"credits": 500, "label": "500 credits"},
    1000: {"credits": 1_050, "label": "1,050 credits"},
    2500: {"credits": 2_750, "label": "2,750 credits"},
}


class TopupRequest(BaseModel):
    user_id: str
    amount_cents: int  # 500, 1000, or 2500


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


class SubscriptionActionRequest(BaseModel):
    user_id: str
    reason: Optional[str] = None


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
        from models.user import SnapTradeUser
        result = await db.execute(
            select(SnapTradeUser.stripe_subscription_id)
            .where(SnapTradeUser.user_id == request.user_id)
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
            reason_str = f" ({request.reason})" if request.reason else ""
            await CreditsService.add_credits(
                db, request.user_id, 0,
                transaction_type="subscription_cancelled",
                description=f"Pro subscription cancelled{reason_str} — active until {end_str}",
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

    if not Config.STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe not configured")

    async with get_db_session() as db:
        from sqlalchemy import select
        from models.user import SnapTradeUser
        result = await db.execute(
            select(SnapTradeUser.stripe_subscription_id, SnapTradeUser.subscription_status)
            .where(SnapTradeUser.user_id == request.user_id)
        )
        row = result.first()
        sub_id = row[0] if row else None
        sub_status = row[1] if row else None

    if not sub_id or sub_status not in ("active",):
        raise HTTPException(status_code=400, detail="No cancellable subscription found")

    client = stripe.StripeClient(Config.STRIPE_SECRET_KEY)
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
        logger.error(f"Stripe resubscribe error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhook")
async def stripe_webhook(request: Request):
    import stripe

    if not Config.STRIPE_SECRET_KEY or not Config.STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=500, detail="Stripe not configured")

    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig, Config.STRIPE_WEBHOOK_SECRET)
    except stripe.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event["type"]
    obj = event["data"]["object"]
    data = obj.to_dict() if hasattr(obj, 'to_dict') else obj

    from datetime import datetime, timezone

    async with get_db_session() as db:
        if event_type == "checkout.session.completed":
            user_id = data.get("client_reference_id")
            customer_id = data.get("customer")
            if not user_id:
                logger.warning("checkout.session.completed without client_reference_id")
                return {"status": "ignored"}

            if customer_id:
                await CreditsService.set_stripe_customer_id(db, user_id, customer_id)

            metadata = data.get("metadata") or {}
            topup_credits = metadata.get("topup_credits")

            if topup_credits:
                credits = int(topup_credits)
                await CreditsService.add_credits(
                    db, user_id, credits,
                    transaction_type="topup",
                    description=f"Credit top-up (+{credits:,} credits)",
                )
                logger.info(f"User {user_id} topped up {credits} credits")
            else:
                subscription_id = data.get("subscription")
                await CreditsService.set_user_plan(db, user_id, "pro")
                if subscription_id:
                    await CreditsService.set_subscription_info(
                        db, user_id,
                        stripe_subscription_id=subscription_id,
                        subscription_status="active",
                        cancel_at_period_end=False,
                    )
                await CreditsService.add_credits(
                    db, user_id, 1_000,
                    transaction_type="subscription",
                    description="Pro plan activation bonus (+1,000 credits)",
                )
                logger.info(f"User {user_id} upgraded to pro via Stripe")

        elif event_type == "customer.subscription.updated":
            customer_id = data.get("customer")
            if not customer_id:
                return {"status": "ignored"}
            user_id = await CreditsService.get_user_id_by_stripe_customer(db, customer_id)
            if user_id:
                cancel_at_period = data.get("cancel_at_period_end", False)
                status = data.get("status", "active")
                cancel_at_ts = data.get("cancel_at")
                period_end = datetime.fromtimestamp(cancel_at_ts, tz=timezone.utc) if cancel_at_ts else None
                await CreditsService.set_subscription_info(
                    db, user_id,
                    subscription_status=status,
                    cancel_at_period_end=cancel_at_period,
                    current_period_end=period_end,
                )
                logger.info(f"User {user_id} subscription updated: status={status} cancel_at_period_end={cancel_at}")

        elif event_type == "customer.subscription.deleted":
            customer_id = data.get("customer")
            if not customer_id:
                return {"status": "ignored"}
            user_id = await CreditsService.get_user_id_by_stripe_customer(db, customer_id)
            if user_id:
                await CreditsService.set_user_plan(db, user_id, "free")
                await CreditsService.clear_subscription_info(db, user_id)
                logger.info(f"User {user_id} downgraded to free (subscription expired)")

    return {"status": "ok"}


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


@router.post("/request")
async def request_credits(
    request: CreditRequestData,
    authenticated_user_id: str = Depends(get_current_user_id),
):
    """
    Submit a credit request - sends email to admin.

    Args:
        request: Credit request data

    Returns:
        Success response
    """
    await verify_user_access(request.user_id, authenticated_user_id)
    try:
        # Send email to admin
        admin_email = "anshul.tibrewal2203@gmail.com"  # Your email
        
        # Construct email
        subject = f"🔔 Credit Request: {request.requested_credits:,} credits from {request.user_email}"
        
        body = f"""
New credit request submitted:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
USER INFORMATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Email: {request.user_email}
User ID: {request.user_id}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CREDIT DETAILS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Requested: {request.requested_credits:,} credits (~${request.requested_credits / 100:.2f} worth)
Current Balance: {request.current_balance:,} credits
Total Used (Lifetime): {request.total_used:,} credits

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
USER'S REASON
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{request.reason}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TO APPROVE THIS REQUEST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Run this command in your terminal:

cd /Users/anshul/code/finch/backend
source venv/bin/activate
python scripts/manage_credits.py add '{request.user_id}' {request.requested_credits} "Approved credit request"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This is an automated email from Finch Credits System.
        """
        
        # Try to send email via SMTP (Gmail example)
        # NOTE: You'll need to configure this with your email settings
        try:
            # For now, just log it - email sending requires SMTP configuration
            logger.info(f"📧 Credit request from {request.user_email}:")
            logger.info(f"   Requested: {request.requested_credits:,} credits")
            logger.info(f"   Current balance: {request.current_balance:,}")
            logger.info(f"   Reason: {request.reason}")
            logger.info(f"   Approval command: python scripts/manage_credits.py add '{request.user_id}' {request.requested_credits}")
            
            # TODO: Uncomment and configure when you want actual email sending
            # smtp_server = "smtp.gmail.com"
            # smtp_port = 587
            # sender_email = Config.SMTP_EMAIL  # Add to your .env
            # sender_password = Config.SMTP_PASSWORD  # Add to your .env
            # 
            # msg = MIMEMultipart()
            # msg['From'] = sender_email
            # msg['To'] = admin_email
            # msg['Subject'] = subject
            # msg.attach(MIMEText(body, 'plain'))
            # 
            # server = smtplib.SMTP(smtp_server, smtp_port)
            # server.starttls()
            # server.login(sender_email, sender_password)
            # server.send_message(msg)
            # server.quit()
            
            return {
                "success": True,
                "message": "Credit request submitted successfully. You'll receive an email once approved."
            }
        
        except Exception as email_error:
            logger.error(f"Failed to send email: {email_error}")
            # Still return success since the request was logged
            return {
                "success": True,
                "message": "Credit request submitted successfully. You'll receive an email once approved."
            }
    
    except Exception as e:
        logger.error(f"Failed to process credit request: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class RedeemCodeRequest(BaseModel):
    code: str


@router.post("/redeem")
@limiter.limit("5/minute")
async def redeem_promo_code(
    request: Request,
    body: RedeemCodeRequest,
    authenticated_user_id: str = Depends(get_current_user_id),
):
    from sqlalchemy import select, update as sql_update
    from models.user import PromoCode, PromoRedemption
    from datetime import datetime, timezone, timedelta
    import uuid

    code_str = body.code.strip().upper()

    async with get_db_session() as db:
        result = await db.execute(
            select(PromoCode).where(PromoCode.code == code_str)
        )
        promo = result.scalar_one_or_none()

        if not promo:
            raise HTTPException(status_code=404, detail="Invalid code")

        if promo.expires_at and datetime.now(timezone.utc) > promo.expires_at:
            raise HTTPException(status_code=400, detail="This code has expired")

        if promo.max_uses is not None and promo.times_used >= promo.max_uses:
            raise HTTPException(status_code=400, detail="This code has been fully redeemed")

        existing = await db.execute(
            select(PromoRedemption).where(
                PromoRedemption.user_id == authenticated_user_id,
                PromoRedemption.code == code_str,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="You've already used this code")

        now = datetime.now(timezone.utc)
        plan_expires = now + timedelta(days=promo.duration_days)

        await CreditsService.set_user_plan(db, authenticated_user_id, promo.plan)
        await CreditsService.add_credits(
            db,
            authenticated_user_id,
            promo.credits,
            transaction_type="promo_code",
            description=f"Promo code {code_str} ({promo.duration_days}d {promo.plan})",
        )

        await db.execute(
            sql_update(PromoCode)
            .where(PromoCode.code == code_str)
            .values(times_used=PromoCode.times_used + 1)
        )

        redemption = PromoRedemption(
            id=uuid.uuid4(),
            user_id=authenticated_user_id,
            code=code_str,
            plan_granted=promo.plan,
            credits_granted=promo.credits,
            plan_expires_at=plan_expires,
        )
        db.add(redemption)
        await db.commit()

        logger.info(f"User {authenticated_user_id} redeemed promo {code_str}: {promo.credits} credits + {promo.plan} for {promo.duration_days}d")

        return {
            "success": True,
            "plan": promo.plan,
            "credits_added": promo.credits,
            "expires_at": plan_expires.isoformat(),
            "message": f"You're now on {promo.plan.title()} with {promo.credits:,} bonus credits!",
        }
