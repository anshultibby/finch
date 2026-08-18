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
#
# Gemini 3.6 Flash with thinking off matches Sonnet's quality on all three of
# these prompts at ~1/5 the cost and ~3x the speed (measured Aug 17 2026).
#
# Requires litellm >= 1.83.7: 1.80.9 dropped `extra_body` on the *Gemini* adapter
# specifically, so `thinking_off_kwargs` below never reached the API and thinking
# silently stayed on. If this is ever downgraded, the failure is silent and
# expensive — with thinking on, ledger_review emits ~476 reasoning tokens against
# its max_tokens=500 and truncates mid-JSON, so `_parse_review` returns None and
# the nightly review is dropped entirely. GLM is unaffected either way; it routes
# through the OpenAI-compatible path, where extra_body passes on both versions.
DEFAULT_INSIGHT_MODEL = Models.GEMINI_3_6_FLASH
OPT_IN_INSIGHT_MODEL = Models.GLM_5_1

# UserSettings.settings is JSONB, so the opt-in needs no migration.
GLM_OPT_IN_KEY = "allow_glm_insights"

# Gemini's only real thinking off-switch. Allowlisted by exact model id rather
# than by provider because support is per-model and asymmetric: 3.6 accepts
# MINIMAL, 3.7 rejects it outright ("Thinking level MINIMAL is not supported for
# this model", HTTP 400) — Google added MINIMAL on the Flash line and then
# dropped it again in 3.7. A wrong entry here fails the call, not just the token
# budget, so anything added must be verified against the live API first.
THINKING_MINIMAL = {"thinkingConfig": {"thinkingLevel": "MINIMAL"}}
_GEMINI_MINIMAL_THINKING = frozenset({Models.GEMINI_3_6_FLASH})

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

    Gemini 3.x also reasons by default, and on these 2-3 sentence prompts it
    spends 90%+ of its output budget doing it — enough to blow past
    ledger_review's max_tokens=500 and return nothing at all. `MINIMAL` is the
    only lever that actually zeroes it: thinkingBudget is a legacy no-op on 3.x
    (budget=100 still yields ~500 reasoning tokens) and `LOW` only trims ~20%.
    """
    if resolve(model).provider == "zai":
        return {"extra_body": {"thinking": {"type": "disabled"}}}
    if model in _GEMINI_MINIMAL_THINKING:
        return {"extra_body": {"generationConfig": THINKING_MINIMAL}}
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
