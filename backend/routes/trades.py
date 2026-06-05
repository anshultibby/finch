"""Trade approval routes — one-click email approval for automation-staged trades.

Flow:
  1. An automation reviews an order and POSTs /trades/request-approval (as the
     user). We stage it in pending_trades and email the user Approve/Reject links.
  2. The user clicks Approve -> GET /trades/approve/{token}. We place the order
     via the Robinhood agentic MCP (server-side, with the user's stored token)
     and show a result page. Reject -> GET /trades/reject/{token}.

The token in the link is the capability, so links expire (default 1h) and are
single-use (a pending trade can only transition out of "pending" once).
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_async_db
from auth.dependencies import get_current_user_id, get_current_user_email
from crud import pending_trades as crud_pending
from services import robinhood_auth
from services.notifications import _send_resend_email
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/trades", tags=["trades"])


# ---------------------------------------------------------------------------
# Request a trade approval (called by automations, as the user)
# ---------------------------------------------------------------------------

class TradeApprovalRequest(BaseModel):
    account_number: str
    # MCP order args: symbol, side, type, quantity|dollar_amount, limit_price, ...
    order_params: dict
    summary: Optional[str] = None  # human-readable preview (e.g. from review_order)
    ttl_minutes: int = 60


def _default_summary(p: dict) -> str:
    qty = p.get("quantity")
    amt = p.get("dollar_amount")
    size = f"${amt}" if amt else f"{qty} sh"
    bits = [str(p.get("side", "")).upper(), size, "of", str(p.get("symbol", "")).upper(),
            f"({p.get('type', 'market')}"]
    if p.get("limit_price"):
        bits.append(f"@ {p['limit_price']}")
    bits.append(")")
    return " ".join(b for b in bits if b).strip()


def _approval_email_html(summary: str, approve_url: str, reject_url: str, expires_at: datetime) -> str:
    when = expires_at.strftime("%b %-d, %-I:%M %p UTC")
    return f"""\
<div style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:520px;margin:0 auto;color:#1c1917;">
  <h2 style="margin:0 0 4px;">Approve this trade?</h2>
  <p style="color:#57534e;margin:0 0 20px;">An automation wants to place an order in your Robinhood agentic account.</p>
  <div style="background:#fafaf9;border:1px solid #e7e5e4;border-radius:10px;padding:16px 20px;font-size:16px;font-weight:600;margin-bottom:24px;">
    {summary}
  </div>
  <a href="{approve_url}" style="display:inline-block;padding:12px 28px;background:#16a34a;color:#fff;text-decoration:none;border-radius:8px;font-weight:700;margin-right:12px;">Approve &amp; place</a>
  <a href="{reject_url}" style="display:inline-block;padding:12px 28px;background:#f5f5f4;color:#1c1917;text-decoration:none;border-radius:8px;font-weight:700;">Reject</a>
  <p style="color:#a8a29e;font-size:13px;margin-top:24px;">This link expires {when}. If it expires, no trade is placed.</p>
</div>"""


@router.post("/request-approval")
async def request_trade_approval(
    body: TradeApprovalRequest,
    user_id: str = Depends(get_current_user_id),
    user_email: Optional[str] = Depends(get_current_user_email),
    db: AsyncSession = Depends(get_async_db),
):
    """Stage a trade and email the user a one-click Approve/Reject link."""
    p = body.order_params or {}
    if not p.get("symbol") or not p.get("side") or not p.get("type"):
        raise HTTPException(status_code=400, detail="order_params must include symbol, side, and type")
    if not (p.get("quantity") or p.get("dollar_amount")):
        raise HTTPException(status_code=400, detail="order_params must include quantity or dollar_amount")

    to_email = user_email or settings_notification_email()
    if not to_email:
        raise HTTPException(status_code=400, detail="No email on file to send the approval link to")

    summary = body.summary or _default_summary(p)
    pt = await crud_pending.create_pending_trade(
        db, user_id=user_id, account_number=body.account_number,
        order_params=p, summary=summary, ttl_minutes=max(5, min(body.ttl_minutes, 1440)),
    )

    base = settings.FINCH_BACKEND_URL.rstrip("/")
    approve_url = f"{base}/trades/approve/{pt.token}"
    reject_url = f"{base}/trades/reject/{pt.token}"
    html = _approval_email_html(summary, approve_url, reject_url, pt.expires_at)
    sent = await _send_resend_email(to_email, "Approve this trade?", html)

    return {
        "token": pt.token,
        "status": pt.status,
        "expires_at": pt.expires_at.isoformat(),
        "email_sent": bool(sent),
        "summary": summary,
    }


def settings_notification_email() -> Optional[str]:
    import os
    return os.getenv("NOTIFICATION_EMAIL")


# ---------------------------------------------------------------------------
# Approve / reject (public links — token is the capability)
# ---------------------------------------------------------------------------

def _page(title: str, body: str, color: str = "#1c1917") -> HTMLResponse:
    html = f"""\
<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title></head>
<body style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;background:#fafaf9;margin:0;">
  <div style="max-width:460px;margin:12vh auto;background:#fff;border:1px solid #e7e5e4;border-radius:14px;padding:32px;text-align:center;">
    <h1 style="color:{color};margin:0 0 12px;font-size:22px;">{title}</h1>
    <div style="color:#57534e;font-size:15px;line-height:1.5;">{body}</div>
  </div>
</body></html>"""
    return HTMLResponse(content=html)


@router.get("/approve/{token}", response_class=HTMLResponse)
async def approve_trade(token: str, db: AsyncSession = Depends(get_async_db)):
    pt = await crud_pending.get_pending_trade_by_token(db, token)
    if not pt:
        return _page("Link not found", "This approval link is invalid.", "#b91c1c")
    if pt.status != "pending":
        return _page("Already handled", f"This trade was already <b>{pt.status}</b>.", "#a16207")
    if datetime.now(timezone.utc) > pt.expires_at:
        await crud_pending.set_pending_trade_status(db, pt, "expired")
        return _page("Link expired", "This approval link expired, so no trade was placed.", "#a16207")

    params = {"account_number": pt.account_number, **pt.order_params}
    try:
        resp = await robinhood_auth.mcp_call(pt.user_id, "place_equity_order", params)
        await crud_pending.set_pending_trade_status(db, pt, "approved", order_response=resp)
        logger.info(f"Pending trade {pt.token} approved + placed for {pt.user_id}")
        return _page("Trade placed ✅", f"<p>{pt.summary}</p><p style='color:#16a34a;'>Your order was submitted to Robinhood.</p>", "#16a34a")
    except Exception as e:
        logger.error(f"Pending trade {pt.token} failed to place: {e}")
        await crud_pending.set_pending_trade_status(db, pt, "failed", error=str(e))
        return _page("Couldn't place trade", f"<p>{pt.summary}</p><p>Robinhood rejected the order: {e}</p>", "#b91c1c")


@router.get("/reject/{token}", response_class=HTMLResponse)
async def reject_trade(token: str, db: AsyncSession = Depends(get_async_db)):
    pt = await crud_pending.get_pending_trade_by_token(db, token)
    if not pt:
        return _page("Link not found", "This approval link is invalid.", "#b91c1c")
    if pt.status != "pending":
        return _page("Already handled", f"This trade was already <b>{pt.status}</b>.", "#a16207")
    await crud_pending.set_pending_trade_status(db, pt, "rejected")
    return _page("Trade rejected", f"<p>{pt.summary}</p><p>No order was placed.</p>")
