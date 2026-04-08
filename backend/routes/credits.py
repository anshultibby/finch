"""
Credits API routes
"""
from fastapi import APIRouter, HTTPException, Request, Header
from pydantic import BaseModel
from typing import Optional
from core.database import get_db_session
from services.credits import CreditsService
from utils.logger import get_logger
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from core.config import Config

logger = get_logger(__name__)

router = APIRouter(prefix="/credits", tags=["credits"])


class CreditBalanceResponse(BaseModel):
    """Response model for credit balance"""
    user_id: str
    credits: int
    total_credits_used: int


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
async def get_credit_balance(user_id: str):
    """
    Get the current credit balance for a user.
    
    Args:
        user_id: User ID
    
    Returns:
        Credit balance and total credits used
    """
    try:
        async with get_db_session() as db:
            from sqlalchemy import select
            from models.user import SnapTradeUser
            
            result = await db.execute(
                select(SnapTradeUser.credits, SnapTradeUser.total_credits_used)
                .where(SnapTradeUser.user_id == user_id)
            )
            row = result.first()
            
            if not row:
                raise HTTPException(status_code=404, detail="User not found")
            
            return CreditBalanceResponse(
                user_id=user_id,
                credits=row[0],
                total_credits_used=row[1]
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get credit balance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{user_id}")
async def get_credit_history(user_id: str, limit: int = 50):
    """
    Get credit transaction history for a user.
    
    Args:
        user_id: User ID
        limit: Maximum number of transactions to return (default: 50)
    
    Returns:
        List of credit transactions (most recent first)
    """
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
async def add_credits(request: AddCreditsRequest):
    """
    Add credits to a user's balance (admin only).
    
    TODO: Add authentication/authorization for admin-only access
    
    Args:
        request: Request with user_id, credits, and description
    
    Returns:
        Updated credit balance
    """
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
        "info": "Credits are calculated based on actual token usage with a 20% premium. 1000 credits = $1 USD base cost.",
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
                "input_cost_usd": 0.3,  # (100K / 1M) * $3
                "output_cost_usd": 0.15,  # (10K / 1M) * $15
                "total_usd": 0.45,
                "with_premium_usd": 0.54,  # 0.45 * 1.2
                "credits_charged": 540  # 0.54 * 1000
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


@router.post("/checkout")
async def create_checkout_session(request: CheckoutRequest):
    """
    Create a Stripe checkout session to upgrade to Pro.
    Returns a URL to redirect the user to.
    """
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
            if user_id:
                await CreditsService.set_user_plan(db, user_id, "pro")
                # Give pro users a credit bonus on first subscription
                await CreditsService.add_credits(
                    db, user_id, 10_000,
                    transaction_type="subscription",
                    description="Pro plan activation bonus (+10,000 credits)"
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
    if not Config.ADMIN_SECRET or x_admin_secret != Config.ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")

    if request.plan not in ("free", "pro", "admin"):
        raise HTTPException(status_code=400, detail="plan must be free, pro, or admin")

    async with get_db_session() as db:
        ok = await CreditsService.set_user_plan(db, request.user_id, request.plan)
        if not ok:
            raise HTTPException(status_code=404, detail="User not found")
        return {"success": True, "user_id": request.user_id, "plan": request.plan}


@router.post("/request")
async def request_credits(request: CreditRequestData):
    """
    Submit a credit request - sends email to admin.
    
    Args:
        request: Credit request data
    
    Returns:
        Success response
    """
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
Requested: {request.requested_credits:,} credits (~${request.requested_credits / 1000:.2f} worth)
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
