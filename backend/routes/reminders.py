from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr
from datetime import date, datetime, timedelta, timezone
from core.database import get_async_db
from auth.dependencies import get_current_user_id, verify_user_access

router = APIRouter(prefix="/reminders", tags=["reminders"])

class CreateReminderRequest(BaseModel):
    user_id: str
    email: str
    symbol_sold: str
    symbol_bought: str | None = None
    loss_amount: float | None = None
    sale_date: date  # the date of the sale

@router.post("")
async def create_reminder(
    req: CreateReminderRequest,
    db: AsyncSession = Depends(get_async_db),
    authenticated_user_id: str = Depends(get_current_user_id),
):
    await verify_user_access(req.user_id, authenticated_user_id)
    from models.user import TLHReminder
    remind_at = datetime.combine(req.sale_date + timedelta(days=61), datetime.min.time()).replace(tzinfo=timezone.utc)
    reminder = TLHReminder(
        user_id=req.user_id,
        email=req.email,
        symbol_sold=req.symbol_sold,
        symbol_bought=req.symbol_bought,
        loss_amount=req.loss_amount,
        sale_date=req.sale_date,
        remind_at=remind_at,
    )
    db.add(reminder)
    await db.commit()
    return {"success": True, "remind_at": remind_at.isoformat(), "id": str(reminder.id)}

@router.get("/user/{user_id}")
async def list_reminders(
    user_id: str,
    db: AsyncSession = Depends(get_async_db),
    authenticated_user_id: str = Depends(get_current_user_id),
):
    await verify_user_access(user_id, authenticated_user_id)
    from models.user import TLHReminder
    from sqlalchemy import select
    result = await db.execute(select(TLHReminder).where(TLHReminder.user_id == user_id).order_by(TLHReminder.remind_at))
    reminders = result.scalars().all()
    return {"reminders": [{"id": str(r.id), "symbol_sold": r.symbol_sold, "symbol_bought": r.symbol_bought, "remind_at": r.remind_at.isoformat(), "sent": r.sent} for r in reminders]}


# ── Alpaca waitlist ──────────────────────────────────────────────────────────

alpaca_router = APIRouter(prefix="/waitlist", tags=["waitlist"])

class WaitlistRequest(BaseModel):
    email: str

@alpaca_router.post("/alpaca")
async def join_alpaca_waitlist(req: WaitlistRequest, db: AsyncSession = Depends(get_async_db)):
    from models.user import AlpacaWaitlist
    from sqlalchemy import select
    # Idempotent — ignore duplicate emails
    existing = await db.execute(select(AlpacaWaitlist).where(AlpacaWaitlist.email == req.email))
    if not existing.scalar_one_or_none():
        db.add(AlpacaWaitlist(email=req.email))
        await db.commit()
    return {"success": True}
