"""
Morning-brief delivery.

Called from the E2B sandbox via the finch_api skill's send_morning_brief()
once the agent has composed the brief. Sends it to the authenticated user by
email (Resend) and push (Expo), and persists it as an in-app notification.
"""
import re

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import text

from auth.dependencies import get_current_user_id
from core.database import get_db_session
from crud.user_preferences import get_user_preferences
from services.monitoring.sink import Push, emit_signal
from services.notifications import send_morning_brief_email, send_morning_brief_whatsapp
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/brief", tags=["brief"])


class BriefSendRequest(BaseModel):
    subject: str = Field(..., min_length=1, max_length=200)
    markdown: str = Field(..., min_length=1, max_length=20_000)
    chat_id: str | None = Field(None, max_length=64)


def _push_preview(markdown: str, limit: int = 160) -> str:
    """First meaningful line of the brief, stripped of markdown syntax."""
    for line in markdown.splitlines():
        plain = re.sub(r"[#*_`>\[\]()-]", "", line).strip()
        if plain:
            return plain[:limit]
    return "Your morning brief is ready."


@router.post("/send")
async def send_brief(
    body: BriefSendRequest,
    user_id: str = Depends(get_current_user_id),
):
    async with get_db_session() as db:
        email = (await db.execute(
            text("SELECT email FROM auth.users WHERE id = CAST(:uid AS uuid)"),
            {"uid": user_id},
        )).scalar()
        prefs = await get_user_preferences(db, user_id)

    from core.config import Config
    chat_url = f"{Config.FRONTEND_URL}/chat/{body.chat_id}" if body.chat_id else None

    email_sent = False
    if email:
        email_sent = await send_morning_brief_email(
            email, body.subject, body.markdown, chat_url
        )

    # One ledger write + the push, together. camelCase in push data: the mobile
    # deep-link handlers key on data.chatId.
    push_sent = await emit_signal(
        user_id, "brief", body.subject, body=_push_preview(body.markdown, 240),
        data={"chat_id": body.chat_id} if body.chat_id else None, source="brief",
        push=Push(
            title=body.subject,
            body=_push_preview(body.markdown),
            notif_type="general",
            data={"chatId": body.chat_id} if body.chat_id else None,
        ),
    )

    whatsapp_sent = False
    phone = (prefs.get("morning_brief_phone") or "").strip()
    if phone:
        whatsapp_sent = await send_morning_brief_whatsapp(phone, body.markdown)

    logger.info(
        f"Morning brief delivered to {user_id}: "
        f"email={email_sent} push={push_sent} whatsapp={whatsapp_sent}"
    )
    return {"email": email_sent, "push": push_sent, "whatsapp": whatsapp_sent}
