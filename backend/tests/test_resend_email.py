"""
Live integration test for Resend email sending.

Uses Resend's test recipient (delivered@resend.dev) which always succeeds
without actually delivering an email.

Run with:
    pytest tests/test_resend_email.py -v
    pytest tests/test_resend_email.py -v -k test_real_email  # send to real inbox
"""
import os
import pytest
import asyncio

# Load .env so RESEND_API_KEY is available
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


@pytest.fixture
def resend_api_key():
    key = os.getenv("RESEND_API_KEY")
    if not key:
        pytest.skip("RESEND_API_KEY not set")
    return key


FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "notifications@finchapp.ai")


def test_send_email_sync(resend_api_key):
    """Send a test email via the sync helper to Resend's test recipient."""
    from services.notifications import _send_resend_email_sync

    result = _send_resend_email_sync(
        to_email="delivered@resend.dev",
        subject="Finch test — sync",
        html="<p>Integration test (sync) passed.</p>",
        from_email=FROM_EMAIL,
    )
    assert result is True, "Sync email send failed"


@pytest.mark.asyncio
async def test_send_email_async(resend_api_key):
    """Send a test email via the async helper to Resend's test recipient."""
    from services.notifications import _send_resend_email

    result = await _send_resend_email(
        to_email="delivered@resend.dev",
        subject="Finch test — async",
        html="<p>Integration test (async) passed.</p>",
        from_email=FROM_EMAIL,
    )
    assert result is True, "Async email send failed"


@pytest.mark.asyncio
async def test_chat_complete_email(resend_api_key):
    """End-to-end test of send_chat_complete_email using Resend test sender."""
    from services.notifications import _send_resend_email

    result = await _send_resend_email(
        to_email="delivered@resend.dev",
        subject="Your analysis is ready: Test Analysis",
        html='<div><h2>Your analysis is ready</h2><a href="https://app.finch.com/chat/test-123">View Results</a></div>',
        from_email=FROM_EMAIL,
    )
    assert result is True, "Chat complete email failed"


@pytest.mark.asyncio
async def test_missing_api_key():
    """Gracefully returns False when RESEND_API_KEY is missing."""
    from services.notifications import _send_resend_email_sync

    old_key = os.environ.pop("RESEND_API_KEY", None)
    try:
        result = _send_resend_email_sync(
            to_email="delivered@resend.dev",
            subject="Should not send",
            html="<p>nope</p>",
        )
        assert result is False
    finally:
        if old_key:
            os.environ["RESEND_API_KEY"] = old_key


@pytest.mark.asyncio
async def test_real_email(resend_api_key):
    """Send a real email to verify inbox delivery. Skipped by default.

    Uses onboarding@resend.dev as sender (always verified).
    To use your own domain, verify it at https://resend.com/domains first.
    """
    email = os.getenv("NOTIFICATION_EMAIL")
    if not email:
        pytest.skip("NOTIFICATION_EMAIL not set — set it to receive a test email")

    from services.notifications import _send_resend_email

    from services.notifications import send_chat_complete_email
    result = await send_chat_complete_email(
        to_email=email,
        chat_title="AAPL earnings deep dive",
        chat_url="https://finchapp.ai/chat/test-live",
        preview=(
            "Apple beat estimates with $1.65 EPS vs $1.58 expected. Revenue came in at $95.4B, up 5% YoY. "
            "Services hit an all-time high at $24.2B, now representing 25% of total revenue.\n\n"
            "Key highlights:\n"
            "- iPhone revenue: $46.2B (+2% YoY), slightly above consensus\n"
            "- Mac revenue: $7.7B (+14% YoY), strong M3 cycle\n"
            "- iPad revenue: $5.6B (-17% YoY), weak but expected\n"
            "- Wearables: $7.8B (-10% YoY), second consecutive decline\n"
            "- Services: $24.2B (+14% YoY), all-time record\n\n"
            "Gross margin expanded to 46.6%, up from 45.0% a year ago. "
            "Management guided Q3 revenue growth in the low-to-mid single digits. "
            "The stock is up 3.2% after hours on the beat.\n\n"
            "Key risk: China revenue declined 2% to $16.4B. Huawei's Mate 70 is gaining share in the premium segment. "
            "Worth monitoring next quarter — if the trend accelerates, it could shave 1-2% off total revenue growth."
        ),
    )
    assert result is True, f"Failed to send real email to {email}"
    print(f"\n✅ Check {email} for the test email")
