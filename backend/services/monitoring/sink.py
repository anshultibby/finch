"""emit_signal — the one way a monitoring pass surfaces a result.

Every pass used to hand-roll "write an AgentEvent to the ledger, and maybe fire
a push." That combo lives here: a single ledger write plus an optional push,
so callers can't drift on event shape or forget the ledger. Email/WhatsApp
fan-out stays in routes/brief.py — the morning brief is the only thing that
uses those channels.
"""
from dataclasses import dataclass
from typing import Optional

from core.database import get_db_session
from services.agent_events import record_event
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Push:
    """A push notification to fire alongside the ledger write."""
    title: str
    body: str
    notif_type: str = "general"
    data: Optional[dict] = None


async def emit_signal(
    user_id: str,
    event_type: str,
    title: str,
    *,
    body: Optional[str] = None,
    data: Optional[dict] = None,
    source: Optional[str] = None,
    value_cents: Optional[int] = None,
    db=None,
    push: Optional[Push] = None,
) -> bool:
    """Record a ledger event and, if `push` is given, send it. Returns whether
    the push was delivered (always False when no push was requested). Like
    record_event, this never raises — a monitoring pass must not die on its sink.
    """
    await record_event(
        user_id, event_type, title, body=body, data=data,
        source=source, value_cents=value_cents, db=db,
    )
    if push is None:
        return False

    from services.push_notifications import send_push_notification
    try:
        async with get_db_session() as session:
            return await send_push_notification(
                session, user_id,
                title=push.title, body=push.body,
                data=push.data, notif_type=push.notif_type,
            )
    except Exception as e:
        logger.warning("emit_signal push failed for %s: %s", user_id, e)
        return False
