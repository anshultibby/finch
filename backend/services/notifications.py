"""
Notification service for trade confirmations.

Supports SMS (Twilio) and email (Resend).
Configure via environment variables:
  - TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER, NOTIFICATION_PHONE
  - RESEND_API_KEY, NOTIFICATION_EMAIL, RESEND_FROM_EMAIL
"""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Base URL for approval links (frontend or API)
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:3000")


def _get_twilio_client():
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")
    if not sid or not token:
        return None
    try:
        from twilio.rest import Client
        return Client(sid, token)
    except ImportError:
        logger.warning("twilio package not installed — pip install twilio")
        return None


def _get_resend_key() -> Optional[str]:
    return os.getenv("RESEND_API_KEY")


async def send_trade_confirmation_sms(
    token: str,
    bot_name: str,
    action: str,
    market: str,
    side: str,
    quantity: int,
    price: float,
    cost_usd: float,
) -> bool:
    """Send SMS asking user to approve/reject a trade. Returns True if sent."""
    phone = os.getenv("NOTIFICATION_PHONE")
    from_number = os.getenv("TWILIO_FROM_NUMBER")
    if not phone or not from_number:
        logger.warning("NOTIFICATION_PHONE or TWILIO_FROM_NUMBER not set")
        return False

    client = _get_twilio_client()
    if not client:
        return False

    approve_url = f"{APP_BASE_URL}/api/trades/approve/{token}"
    reject_url = f"{APP_BASE_URL}/api/trades/reject/{token}"

    body = (
        f"{bot_name} wants to {action.upper()}:\n"
        f"{market}\n"
        f"Side: {side} | Qty: {quantity} | Price: {price}c\n"
        f"Cost: ${cost_usd:.2f}\n\n"
        f"APPROVE: {approve_url}\n"
        f"REJECT: {reject_url}"
    )

    try:
        msg = client.messages.create(
            body=body,
            from_=from_number,
            to=phone,
        )
        logger.info(f"Trade confirmation SMS sent: {msg.sid}")
        return True
    except Exception as e:
        logger.error(f"Failed to send SMS: {e}")
        return False


def _send_resend_email(to_email: str, subject: str, html: str, from_email: Optional[str] = None) -> bool:
    """Send an email via Resend. Returns True if sent successfully."""
    from_email = from_email or os.getenv("RESEND_FROM_EMAIL", "finch@finch.app")
    api_key = _get_resend_key()

    if not api_key or not to_email:
        logger.warning("RESEND_API_KEY or to_email not set")
        return False

    try:
        import resend
        resend.api_key = api_key
    except ImportError:
        logger.warning("resend package not installed — pip install resend")
        return False

    try:
        resend.Emails.send({
            "from": from_email,
            "to": [to_email],
            "subject": subject,
            "html": html,
        })
        logger.info(f"Email sent to {to_email}: {subject}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False


async def send_trade_confirmation_email(
    token: str,
    bot_name: str,
    action: str,
    market: str,
    side: str,
    quantity: int,
    price: float,
    cost_usd: float,
) -> bool:
    """Send email asking user to approve/reject a trade. Returns True if sent."""
    to_email = os.getenv("NOTIFICATION_EMAIL")
    if not to_email:
        logger.warning("NOTIFICATION_EMAIL not set")
        return False

    approve_url = f"{APP_BASE_URL}/api/trades/approve/{token}"
    reject_url = f"{APP_BASE_URL}/api/trades/reject/{token}"

    subject = f"{bot_name}: Confirm {action.upper()} {market}"
    html = f"""
    <h2>{bot_name} wants to {action.upper()}</h2>
    <table style="border-collapse:collapse;">
      <tr><td style="padding:4px 12px;font-weight:bold;">Market</td><td style="padding:4px 12px;">{market}</td></tr>
      <tr><td style="padding:4px 12px;font-weight:bold;">Side</td><td style="padding:4px 12px;">{side}</td></tr>
      <tr><td style="padding:4px 12px;font-weight:bold;">Quantity</td><td style="padding:4px 12px;">{quantity}</td></tr>
      <tr><td style="padding:4px 12px;font-weight:bold;">Price</td><td style="padding:4px 12px;">{price}c</td></tr>
      <tr><td style="padding:4px 12px;font-weight:bold;">Cost</td><td style="padding:4px 12px;">${cost_usd:.2f}</td></tr>
    </table>
    <br/>
    <a href="{approve_url}" style="display:inline-block;padding:12px 24px;background:#16a34a;color:white;text-decoration:none;border-radius:6px;font-weight:bold;margin-right:12px;">APPROVE</a>
    <a href="{reject_url}" style="display:inline-block;padding:12px 24px;background:#dc2626;color:white;text-decoration:none;border-radius:6px;font-weight:bold;">REJECT</a>
    """

    return _send_resend_email(to_email, subject, html, os.getenv("RESEND_FROM_EMAIL", "trades@finch.app"))


async def send_chat_complete_email(to_email: str, chat_title: str, chat_url: str) -> bool:
    """Send email notifying user their chat analysis is ready."""
    subject = f"Your analysis is ready: {chat_title}"
    html = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 480px; margin: 0 auto; padding: 24px;">
      <h2 style="color: #111827; margin-bottom: 8px;">Your analysis is ready</h2>
      <p style="color: #6b7280; font-size: 14px; margin-bottom: 24px;">
        {chat_title}
      </p>
      <a href="{chat_url}" style="display:inline-block;padding:12px 24px;background:#2563eb;color:white;text-decoration:none;border-radius:8px;font-weight:600;">
        View Results
      </a>
    </div>
    """

    return _send_resend_email(to_email, subject, html)


async def send_trade_notification(
    token: str,
    bot_name: str,
    action: str,
    market: str,
    side: str,
    quantity: int,
    price: float,
    cost_usd: float,
) -> str:
    """Try SMS first, fall back to email. Returns the method used or 'none'."""
    kwargs = dict(
        token=token,
        bot_name=bot_name,
        action=action,
        market=market,
        side=side,
        quantity=quantity,
        price=price,
        cost_usd=cost_usd,
    )
    if await send_trade_confirmation_sms(**kwargs):
        return "sms"
    if await send_trade_confirmation_email(**kwargs):
        return "email"
    logger.warning("No notification channel configured — trade will auto-execute")
    return "none"
