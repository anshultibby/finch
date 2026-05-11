"""Background task that checks for due TLH reminders and sends them via email."""
import asyncio
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

async def send_due_reminders():
    from core.database import get_db_session
    from models.user import TLHReminder
    from sqlalchemy import select
    import os

    now = datetime.now(timezone.utc)
    async with get_db_session() as db:
        result = await db.execute(
            select(TLHReminder).where(
                TLHReminder.sent == False,
                TLHReminder.remind_at <= now
            )
        )
        due = result.scalars().all()

        for reminder in due:
            try:
                await _send_reminder_email(reminder)
                reminder.sent = True
                reminder.sent_at = now
                logger.info(f"Sent TLH reminder to {reminder.email} for {reminder.symbol_sold}")
            except Exception as e:
                logger.error(f"Failed to send reminder {reminder.id}: {e}")

        if due:
            await db.commit()

async def _send_reminder_email(reminder):
    from services.notifications import _send_resend_email

    repurchase_symbol = reminder.symbol_sold
    html = f"""
    <div style="font-family: sans-serif; max-width: 480px; margin: 0 auto; padding: 32px 24px;">
      <h2 style="color: #111; margin-bottom: 8px;">Wash sale window cleared for {repurchase_symbol}</h2>
      <p style="color: #555;">It's been 61 days since you harvested your loss on <strong>{reminder.symbol_sold}</strong>.</p>
      <p style="color: #555;">You can now safely repurchase <strong>{reminder.symbol_sold}</strong> without triggering the wash sale rule.</p>
      {f'<p style="color: #555;">Your estimated tax savings from this harvest: <strong>${reminder.loss_amount:,.0f}</strong></p>' if reminder.loss_amount else ''}
      <p style="color: #888; font-size: 13px; margin-top: 24px;">This reminder was set on Finch.</p>
    </div>
    """
    sent = await _send_resend_email(
        reminder.email,
        f"You can now repurchase {repurchase_symbol} — wash sale window cleared",
        html,
    )
    if not sent:
        raise RuntimeError(f"Failed to send reminder email to {reminder.email}")

async def run_reminder_loop():
    """Run forever, checking every hour."""
    while True:
        try:
            await send_due_reminders()
        except Exception as e:
            logger.error(f"Reminder loop error: {e}")
        await asyncio.sleep(3600)  # check every hour
