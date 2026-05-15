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

logger = get_logger(__name__)

router = APIRouter(prefix="/credits", tags=["credits"])


class CreditBalanceResponse(BaseModel):
    """Response model for credit balance"""
    user_id: str
    credits: int
    total_credits_used: int
    plan: str = "free"


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
                select(SnapTradeUser.credits, SnapTradeUser.total_credits_used, SnapTradeUser.plan)
                .where(SnapTradeUser.user_id == user_id)
            )
            row = result.first()

            if not row:
                raise HTTPException(status_code=404, detail="User not found")

            return CreditBalanceResponse(
                user_id=user_id,
                credits=row[0],
                total_credits_used=row[1],
                plan=row[2] or "free",
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
    success_url: str
    cancel_url: str


class SetPlanRequest(BaseModel):
    user_id: str
    plan: str  # free | pro | admin


class PromoRequestBody(BaseModel):
    email: str
    message: str = ""


@router.post("/request-code")
async def request_promo_code(body: PromoRequestBody):
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
    """
    Create a Stripe checkout session to upgrade to Pro.
    Returns a URL to redirect the user to.
    """
    await verify_user_access(request.user_id, authenticated_user_id)
    try:
        import stripe
    except ImportError:
        raise HTTPException(status_code=500, detail="Stripe not installed")

    if not Config.STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    if not Config.STRIPE_PRO_PRICE_ID:
        raise HTTPException(status_code=500, detail="Stripe Pro price not configured")

    stripe.api_key = Config.STRIPE_SECRET_KEY
    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": Config.STRIPE_PRO_PRICE_ID, "quantity": 1}],
            success_url=request.success_url,
            cancel_url=request.cancel_url,
            metadata={"user_id": request.user_id},
        )
        return {"url": session.url, "session_id": session.id}
    except Exception as e:
        logger.error(f"Stripe checkout error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class PortalRequest(BaseModel):
    user_id: str
    return_url: str


@router.post("/portal")
async def create_portal_session(
    request: PortalRequest,
    authenticated_user_id: str = Depends(get_current_user_id),
):
    """Create a Stripe Billing Portal session so users can cancel/manage their subscription."""
    await verify_user_access(request.user_id, authenticated_user_id)
    try:
        import stripe
    except ImportError:
        raise HTTPException(status_code=500, detail="Stripe not installed")

    if not Config.STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe not configured")

    stripe.api_key = Config.STRIPE_SECRET_KEY

    async with get_db_session() as db:
        customer_id = await CreditsService.get_stripe_customer_id(db, request.user_id)

    if not customer_id:
        raise HTTPException(status_code=400, detail="No active subscription found")

    try:
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=request.return_url,
        )
        return {"url": session.url}
    except Exception as e:
        logger.error(f"Stripe portal error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """
    Stripe webhook handler. Upgrades user to Pro on successful payment.
    Configure in Stripe dashboard: checkout.session.completed + customer.subscription.deleted
    """
    try:
        import stripe
    except ImportError:
        raise HTTPException(status_code=500, detail="Stripe not installed")

    if not Config.STRIPE_SECRET_KEY or not Config.STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=500, detail="Stripe not configured")

    stripe.api_key = Config.STRIPE_SECRET_KEY
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig, Config.STRIPE_WEBHOOK_SECRET)
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    async with get_db_session() as db:
        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            user_id = session.get("metadata", {}).get("user_id")
            customer_id = session.get("customer")
            if user_id:
                await CreditsService.set_user_plan(db, user_id, "pro")
                if customer_id:
                    await CreditsService.set_stripe_customer_id(db, user_id, customer_id)
                await CreditsService.add_credits(
                    db, user_id, 1_000,
                    transaction_type="subscription",
                    description="Pro plan activation bonus (+1,000 credits / $10)"
                )
                logger.info(f"User {user_id} upgraded to pro via Stripe")

        elif event["type"] == "customer.subscription.deleted":
            session = event["data"]["object"]
            user_id = session.get("metadata", {}).get("user_id")
            if user_id:
                await CreditsService.set_user_plan(db, user_id, "free")
                logger.info(f"User {user_id} downgraded to free (subscription cancelled)")

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
async def redeem_promo_code(
    request: RedeemCodeRequest,
    authenticated_user_id: str = Depends(get_current_user_id),
):
    from sqlalchemy import select, update as sql_update
    from models.user import PromoCode, PromoRedemption
    from datetime import datetime, timezone, timedelta
    import uuid

    code_str = request.code.strip().upper()

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
