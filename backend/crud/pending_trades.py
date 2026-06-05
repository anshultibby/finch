"""CRUD for pending_trades — trades staged by automations for one-click email approval.

Standalone, not bot-coupled. See models.brokerage.PendingTrade and routes/trades.py.
"""
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.brokerage import PendingTrade


async def create_pending_trade(
    db: AsyncSession,
    user_id: str,
    account_number: str,
    order_params: dict,
    summary: Optional[str] = None,
    broker: str = "robinhood",
    ttl_minutes: int = 60,
) -> PendingTrade:
    """Stage a trade and mint a single-use approval token."""
    pt = PendingTrade(
        user_id=user_id,
        token=secrets.token_urlsafe(32),
        broker=broker,
        account_number=account_number,
        order_params=order_params,
        summary=summary,
        status="pending",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes),
    )
    db.add(pt)
    await db.commit()
    await db.refresh(pt)
    return pt


async def get_pending_trade_by_token(db: AsyncSession, token: str) -> Optional[PendingTrade]:
    result = await db.execute(select(PendingTrade).where(PendingTrade.token == token))
    return result.scalars().first()


async def set_pending_trade_status(
    db: AsyncSession,
    pt: PendingTrade,
    status: str,
    order_response: Optional[dict] = None,
    error: Optional[str] = None,
) -> PendingTrade:
    """Transition a pending trade to a terminal state (approved/rejected/expired/failed)."""
    pt.status = status
    pt.decided_at = datetime.now(timezone.utc)
    if order_response is not None:
        pt.order_response = order_response
    if error is not None:
        pt.error = error
    await db.commit()
    await db.refresh(pt)
    return pt
