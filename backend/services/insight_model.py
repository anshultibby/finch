"""Per-tenant model policy + activity gating for the passive insight jobs.

Three jobs (portfolio digest, nightly ledger review, why-is-it-moving) send a
user's actual holdings — symbols, quantities, position values — to an LLM. GLM
routes to Z.ai / Zhipu, which is China-based, so it is **opt-in per tenant** and
off by default; everyone else gets a US-hosted model. See
`docs/hedge-fund-gtm-research.md` §6d for why this gates any advisor/RIA sale.

These jobs also run unattended for every user who has ever added a watchlist
symbol, which is pure spend on accounts nobody is reading. `is_user_active`
keeps them scoped to users who have actually shown up recently.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, Set

from sqlalchemy import func, or_, select

from core.constants import Models
from core.database import get_db_session
from core.model_registry import resolve
from models.chat_models import Chat
from models.user import SnapTradeUser, UserSettings

logger = logging.getLogger(__name__)

# US-hosted default. GLM stays wired up but has to be turned on per tenant.
DEFAULT_INSIGHT_MODEL = Models.CLAUDE_SONNET_4_6
OPT_IN_INSIGHT_MODEL = Models.GLM_5_1

# UserSettings.settings is JSONB, so the opt-in needs no migration.
GLM_OPT_IN_KEY = "allow_glm_insights"

# A user counts as active if they've opened a chat or synced a brokerage within
# this window. Everything upstream of the insight jobs is best-effort, so the
# window is deliberately generous — this is a spend filter, not an auth check.
ACTIVE_WINDOW_DAYS = 14


async def resolve_insight_model(user_id: str) -> str:
    """The model to use for `user_id`'s insight jobs.

    Defaults to the US-hosted model; returns GLM only for tenants that have
    explicitly opted in. Any lookup failure falls back to the default — the
    safe direction, since the failure mode we care about is *accidentally*
    sending holdings to the opt-in provider.
    """
    try:
        async with get_db_session() as db:
            result = await db.execute(
                select(UserSettings.settings).where(UserSettings.user_id == user_id)
            )
            settings = result.scalar_one_or_none() or {}
    except Exception:
        logger.warning("insight model lookup failed for %s; using default", user_id)
        return DEFAULT_INSIGHT_MODEL

    if (settings or {}).get(GLM_OPT_IN_KEY) is True:
        return OPT_IN_INSIGHT_MODEL
    return DEFAULT_INSIGHT_MODEL


def thinking_off_kwargs(model: str) -> Dict[str, Any]:
    """Completion kwargs that keep these short generations non-reasoning.

    Z.ai turns reasoning on server-side, so GLM needs an explicit opt-out (it
    otherwise adds ~30s per call). Anthropic only thinks when asked, and these
    call sites never pass `reasoning_params`, so there's nothing to disable.
    """
    if resolve(model).provider == "zai":
        return {"extra_body": {"thinking": {"type": "disabled"}}}
    return {}


async def filter_active_users(user_ids: Iterable[str]) -> Set[str]:
    """Narrow `user_ids` to those seen within ACTIVE_WINDOW_DAYS.

    On error every candidate is returned — degrading to the old
    everyone-gets-one behavior beats silently dropping a live user's digest.
    """
    candidates = {uid for uid in user_ids if uid}
    if not candidates:
        return set()

    cutoff = datetime.now(timezone.utc) - timedelta(days=ACTIVE_WINDOW_DAYS)
    active: Set[str] = set()
    try:
        async with get_db_session() as db:
            chatted = await db.execute(
                select(Chat.user_id)
                .where(Chat.user_id.in_(candidates), Chat.updated_at >= cutoff)
                .distinct()
            )
            active.update(uid for (uid,) in chatted.all())

            synced = await db.execute(
                select(SnapTradeUser.user_id).where(
                    SnapTradeUser.user_id.in_(candidates),
                    SnapTradeUser.last_activity >= cutoff,
                )
            )
            active.update(uid for (uid,) in synced.all())
    except Exception:
        logger.exception("active-user filter failed; processing all candidates")
        return candidates

    skipped = len(candidates) - len(active)
    if skipped:
        logger.info(
            "insight jobs: skipping %d inactive user(s) of %d", skipped, len(candidates)
        )
    return active
