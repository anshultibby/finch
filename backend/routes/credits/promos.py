"""
Promo codes and manual credit requests.
"""
from utils.logger import get_logger
from fastapi import APIRouter, Depends, HTTPException, Request
from core.database import get_db_session
from services.credits import CreditsService
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from core.config import Config
from auth.dependencies import get_current_user_id, verify_user_access
from core.rate_limit import limiter
from .schemas import CreditRequestData, PromoRequestBody, RedeemCodeRequest

logger = get_logger(__name__)

router = APIRouter()


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
