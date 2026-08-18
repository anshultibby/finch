"""
Notification service for trade confirmations.

Supports SMS (Twilio) and email (Resend).
Configure via environment variables:
  - TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER, NOTIFICATION_PHONE
  - RESEND_API_KEY, NOTIFICATION_EMAIL, RESEND_FROM_EMAIL
"""
import os
import logging
import asyncio
from functools import partial
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


def _send_resend_email_sync(to_email: str, subject: str, html: str, from_email: Optional[str] = None) -> bool:
    """Send an email via Resend (blocking). Use send_resend_email() in async code."""
    raw = from_email or os.getenv("RESEND_FROM_EMAIL", "notifications@finchapp.ai")
    from_email = f"Finch <{raw}>" if raw and "<" not in raw else raw
    api_key = _get_resend_key()

    if not api_key:
        logger.warning("RESEND_API_KEY not set — cannot send email")
        return False
    if not to_email:
        logger.warning("No recipient email — cannot send email")
        return False

    try:
        import resend
        resend.api_key = api_key
    except ImportError:
        logger.warning("resend package not installed — pip install resend")
        return False

    try:
        result = resend.Emails.send({
            "from": from_email,
            "to": [to_email],
            "subject": subject,
            "html": html,
        })
        email_id = result.get("id") if isinstance(result, dict) else getattr(result, "id", None)
        logger.info(f"Email sent to {to_email}: {subject} (id={email_id})")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False


async def _send_resend_email(to_email: str, subject: str, html: str, from_email: Optional[str] = None) -> bool:
    """Async wrapper — runs the blocking Resend SDK call in a thread."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None, partial(_send_resend_email_sync, to_email, subject, html, from_email)
    )


def _markdown_to_email_html(text: str) -> str:
    """Convert markdown text to inline-styled HTML suitable for email clients."""
    import markdown as md

    rendered = md.markdown(text, extensions=["tables", "fenced_code", "nl2br"])

    # Inline styles for email compatibility (email clients strip <style> blocks)
    style_map = {
        "<h1": '<h1 style="color:#0f172a;font-size:20px;font-weight:700;margin:16px 0 8px;line-height:1.3;"',
        "<h2": '<h2 style="color:#0f172a;font-size:18px;font-weight:700;margin:16px 0 8px;line-height:1.3;"',
        "<h3": '<h3 style="color:#0f172a;font-size:16px;font-weight:600;margin:12px 0 6px;line-height:1.3;"',
        "<h4": '<h4 style="color:#1e293b;font-size:15px;font-weight:600;margin:10px 0 4px;line-height:1.3;"',
        "<p>": '<p style="color:#1e293b;font-size:15px;line-height:1.7;margin:0 0 12px;">',
        "<ul>": '<ul style="color:#1e293b;font-size:15px;line-height:1.7;margin:0 0 12px;padding-left:24px;">',
        "<ol>": '<ol style="color:#1e293b;font-size:15px;line-height:1.7;margin:0 0 12px;padding-left:24px;">',
        "<li>": '<li style="margin:0 0 4px;">',
        "<strong>": '<strong style="font-weight:600;color:#0f172a;">',
        "<em>": '<em style="color:#334155;">',
        "<code>": '<code style="background:#f1f5f9;padding:2px 6px;border-radius:4px;font-size:13px;font-family:ui-monospace,monospace;color:#475569;">',
        "<pre>": '<pre style="background:#f1f5f9;border-radius:8px;padding:16px;overflow-x:auto;margin:0 0 12px;">',
        "<table>": '<table style="border-collapse:collapse;width:100%;margin:0 0 12px;font-size:14px;">',
        "<th": '<th style="text-align:left;padding:8px 12px;border-bottom:2px solid #e2e8f0;font-weight:600;color:#0f172a;"',
        "<td": '<td style="padding:8px 12px;border-bottom:1px solid #f1f5f9;color:#1e293b;"',
        "<blockquote>": '<blockquote style="border-left:3px solid #4ABA8E;margin:0 0 12px;padding:8px 16px;color:#475569;background:#f4faf7;border-radius:0 8px 8px 0;">',
        "<hr": '<hr style="border:none;border-top:1px solid #e2e8f0;margin:20px 0;"',
        "<a ": '<a style="color:#4ABA8E;text-decoration:underline;" ',
    }
    for tag, styled in style_map.items():
        rendered = rendered.replace(tag, styled)

    return rendered


async def send_chat_complete_email(to_email: str, chat_title: str, chat_url: str, preview: str = None) -> bool:
    """Send email notifying user their chat analysis is ready."""
    import html as html_mod
    subject = chat_title

    safe_title = html_mod.escape(chat_title)

    preview_section = ""
    if preview:
        preview_html = _markdown_to_email_html(preview)
        preview_section = f"""
        <div style="background: #f8fafc; border-radius: 12px; padding: 20px 24px; margin: 0 0 28px 0; border: 1px solid #e2e8f0;">
          {preview_html}
        </div>
        """

    logo_svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" fill="none" '
        'width="40" height="40" style="vertical-align: middle;">'
        '<rect width="512" height="512" rx="112" fill="#4ABA8E"/>'
        '<rect x="148" y="160" width="56" height="192" rx="28" fill="white"/>'
        '<rect x="228" y="120" width="56" height="272" rx="28" fill="white"/>'
        '<rect x="308" y="200" width="56" height="152" rx="28" fill="white"/>'
        '</svg>'
    )

    body_html = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 680px; margin: 0 auto; padding: 0;">
      <!-- Header -->
      <div style="background: #fafaf9; padding: 28px 28px 20px; border-radius: 12px 12px 0 0; border: 1px solid rgba(0,0,0,0.06); border-bottom: none;">
        <div style="margin-bottom: 20px;">
          {logo_svg}
        </div>
        <h1 style="color: #0f172a; font-size: 22px; font-weight: 600; margin: 0 0 6px 0; line-height: 1.3;">{safe_title}</h1>
        <p style="color: #64748b; font-size: 14px; margin: 0;">Your research is ready</p>
      </div>

      <!-- Body -->
      <div style="background: #ffffff; padding: 24px 28px 28px; border: 1px solid rgba(0,0,0,0.06); border-top: none; border-bottom: none;">
        {preview_section}
        <a href="{chat_url}" style="display: inline-block; padding: 14px 32px; background: #4ABA8E; color: #ffffff; text-decoration: none; border-radius: 10px; font-weight: 600; font-size: 15px;">
          See full analysis &rarr;
        </a>
      </div>

      <!-- Footer -->
      <div style="padding: 16px 28px; border: 1px solid rgba(0,0,0,0.06); border-top: none; border-radius: 0 0 12px 12px; background: #fafaf9;">
        <p style="color: #94a3b8; font-size: 12px; margin: 0;">
          <a href="https://finchapp.ai" style="color: #94a3b8; text-decoration: none;">finchapp.ai</a>
        </p>
      </div>
    </div>
    """

    return await _send_resend_email(to_email, subject, body_html)


def _markdown_to_whatsapp(text: str) -> str:
    """Convert brief markdown to WhatsApp formatting (single-asterisk bold,
    no headings), truncated to WhatsApp's message limit."""
    import re
    out = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped in ("---", "***"):
            continue
        # "## Heading" -> "*Heading*"
        m = re.match(r"^#{1,6}\s+(.*)$", stripped)
        if m:
            out.append(f"*{m.group(1).strip()}*")
            continue
        # "**bold**" -> "*bold*"
        out.append(re.sub(r"\*\*(.+?)\*\*", r"*\1*", line))
    result = "\n".join(out).strip()
    return result[:3900]  # WhatsApp cap is 4096; leave headroom


async def send_morning_brief_whatsapp(to_number: str, markdown_body: str) -> bool:
    """Send the morning brief over WhatsApp via Twilio.

    Free-form messages only deliver inside a 24h session (sandbox: the user
    must have joined and messaged recently). Outside the window Twilio accepts
    the message but WhatsApp drops it (error 63016 on the message resource) —
    production daily delivery needs an approved Content Template.
    """
    from_number = os.getenv("TWILIO_WHATSAPP_FROM")
    client = _get_twilio_client()
    if not client or not from_number:
        logger.warning("Twilio WhatsApp not configured (TWILIO_* env vars)")
        return False

    to = to_number if to_number.startswith("whatsapp:") else f"whatsapp:{to_number}"

    def _send():
        return client.messages.create(
            body=_markdown_to_whatsapp(markdown_body),
            from_=from_number,
            to=to,
        )

    try:
        loop = asyncio.get_event_loop()
        msg = await loop.run_in_executor(None, _send)
        logger.info(f"Morning brief WhatsApp sent: {msg.sid} (status={msg.status})")
        return True
    except Exception as e:
        logger.error(f"Failed to send WhatsApp brief: {e}")
        return False


async def send_morning_brief_email(
    to_email: str, subject: str, markdown_body: str, chat_url: Optional[str] = None
) -> bool:
    """Send the daily morning brief (agent-written markdown) as a styled email."""
    body_inner = _markdown_to_email_html(markdown_body)

    logo_svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" fill="none" '
        'width="32" height="32" style="vertical-align: middle;">'
        '<rect width="512" height="512" rx="112" fill="#4ABA8E"/>'
        '<rect x="148" y="160" width="56" height="192" rx="28" fill="white"/>'
        '<rect x="228" y="120" width="56" height="272" rx="28" fill="white"/>'
        '<rect x="308" y="200" width="56" height="152" rx="28" fill="white"/>'
        '</svg>'
    )

    cta = ""
    if chat_url:
        cta = (
            f'<a href="{chat_url}" style="display: inline-block; margin-top: 8px; padding: 12px 28px; '
            'background: #4ABA8E; color: #ffffff; text-decoration: none; border-radius: 10px; '
            'font-weight: 600; font-size: 14px;">Open in Finch &rarr;</a>'
        )

    html = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 680px; margin: 0 auto; padding: 0;">
      <div style="background: #fafaf9; padding: 24px 28px 16px; border-radius: 12px 12px 0 0; border: 1px solid rgba(0,0,0,0.06); border-bottom: none;">
        {logo_svg}
        <p style="color: #64748b; font-size: 13px; margin: 12px 0 0; text-transform: uppercase; letter-spacing: 0.05em;">Your morning brief</p>
      </div>
      <div style="background: #ffffff; padding: 24px 28px 28px; border: 1px solid rgba(0,0,0,0.06); border-top: none; border-bottom: none;">
        {body_inner}
        {cta}
      </div>
      <div style="padding: 16px 28px; border: 1px solid rgba(0,0,0,0.06); border-top: none; border-radius: 0 0 12px 12px; background: #fafaf9;">
        <p style="color: #94a3b8; font-size: 12px; margin: 0;">
          Daily brief from <a href="https://finchapp.ai" style="color: #94a3b8; text-decoration: none;">finchapp.ai</a>
          &mdash; pause it any time in Automations. Not financial advice.
        </p>
      </div>
    </div>
    """

    return await _send_resend_email(to_email, subject, html)


