"""
Nightly ledger review — cheap general analysis of each user's watchlist +
portfolio, written into the agent-activity ledger as an `insight` event.

This is deliberately NOT an agent run (no tool loop, no sandbox): the stats
are computed deterministically from one FMP batch-quote call, and a
single completion (thinking disabled, same pattern as the why-engine) narrates
them. Cost is a fraction of a cent per active user per day — it's what makes
the "while you were gone" ledger feel alive even for users with no automations
or trades. The model is resolved per tenant; see services.insight_model.

Dedup is DB-backed (one `insight` event per user per ET trading day), so
overlapping dev/prod instances or restarts can't double-write.
"""
import asyncio
import json
import logging
import re
from datetime import datetime, time as dtime, timezone
from typing import Dict, List, Optional, Set
from zoneinfo import ZoneInfo

from sqlalchemy import select

from core.database import get_db_session
from models.activity import AgentEvent
from models.brokerage import PortfolioHoldingsCache, UserWatchlist
from services.insight_model import filter_active_users
from services.monitoring.inputs import batch_quotes, holdings_qty
from services.monitoring.narrate import narrate
from services.monitoring.sink import emit_signal

logger = logging.getLogger(__name__)

ET = ZoneInfo("America/New_York")

# The model is resolved per user (see services.insight_model) — GLM is opt-in.
# The sweep only fires once per user per day, so a slow tick costs nothing but
# saves 5 wake-ups an hour on a job that is idle outside the review window.
CHECK_INTERVAL_SECONDS = 60 * 60
MAX_SYMBOLS_PER_USER = 40
MAX_REVIEWS_PER_SWEEP = 500  # global safety valve

_SYSTEM_PROMPT = """You are Finch's agent writing its nightly review into the user's activity ledger. You get computed market stats for the symbols they hold or watch (already correct — never recompute or contradict them).

Return STRICT JSON, nothing else:
{"title": "...", "body": "..."}

- title: ONE punchy takeaway, <= 80 chars, the single most decision-relevant fact tonight (e.g. "NVDA closed 3% off its 52-week high on double volume").
- body: 2-3 more observations, each on its own line, each <= 120 chars. Plain English, no bullets/emojis/headers.
- Only use the data given. Never invent news or numbers. Prefer what a holder would act on: unusual volume, 52-week proximity, outsized moves, portfolio concentration."""


def _in_review_window(now_et: datetime) -> bool:
    """Weekdays after the close (4:15pm ET onward)."""
    return now_et.weekday() < 5 and now_et.time() >= dtime(16, 15)


async def _gather_users() -> Dict[str, Dict[str, float]]:
    """user_id -> {symbol: quantity} for recently-active users with symbols.

    Unlike the market monitor this does NOT require a push device — the
    review lands in the in-app ledger, which every platform can read. It is
    gated on recent activity though: a watchlist row from a user who churned
    months ago would otherwise buy a review nobody opens, every trading day,
    forever.
    """
    async with get_db_session() as db:
        users: Dict[str, Dict[str, float]] = {}
        result = await db.execute(select(UserWatchlist.user_id, UserWatchlist.symbol))
        for uid, sym in result.all():
            users.setdefault(uid, {}).setdefault(sym.upper(), 0.0)
        result = await db.execute(
            select(PortfolioHoldingsCache.user_id, PortfolioHoldingsCache.portfolio_data)
        )
        for uid, data in result.all():
            for sym, qty in holdings_qty(data).items():
                cur = users.setdefault(uid, {})
                cur[sym] = max(cur.get(sym, 0.0), qty)

    active = await filter_active_users(users.keys())
    return {uid: syms for uid, syms in users.items() if uid in active}


async def _reviewed_today(user_ids: Set[str], day_start_utc: datetime) -> Set[str]:
    if not user_ids:
        return set()
    async with get_db_session() as db:
        result = await db.execute(
            select(AgentEvent.user_id).where(
                AgentEvent.user_id.in_(user_ids),
                AgentEvent.event_type == "insight",
                AgentEvent.created_at >= day_start_utc,
            ).group_by(AgentEvent.user_id)
        )
        return {row[0] for row in result.all()}


def _stat_lines(symbols: Dict[str, float], quotes: Dict[str, dict]) -> List[str]:
    """Deterministic per-symbol facts the LLM narrates from."""
    rows = []
    for sym, qty in symbols.items():
        q = quotes.get(sym)
        if not q or q.get("price") is None:
            continue
        price = float(q.get("price") or 0)
        pct = float(q.get("changesPercentage") or 0)
        facts = [f"{sym}: {pct:+.2f}% to ${price:,.2f}"]
        if qty:
            facts.append(f"user holds {qty:g} sh (~${qty * price:,.0f})")
        year_high = float(q.get("yearHigh") or 0)
        year_low = float(q.get("yearLow") or 0)
        if year_high and price:
            off_high = (year_high - price) / year_high * 100
            if off_high <= 3:
                facts.append(f"{off_high:.1f}% below 52w high")
        if year_low and price:
            above_low = (price - year_low) / year_low * 100
            if above_low <= 5:
                facts.append(f"only {above_low:.1f}% above 52w low")
        vol = float(q.get("volume") or 0)
        avg_vol = float(q.get("avgVolume") or 0)
        if vol and avg_vol and vol / avg_vol >= 1.8:
            facts.append(f"volume {vol / avg_vol:.1f}x average")
        rows.append((abs(pct), " — ".join(facts)))
    rows.sort(key=lambda r: r[0], reverse=True)
    return [r[1] for r in rows[:12]]


async def _narrate(
    lines: List[str], spy_pct: Optional[float], user_id: str
) -> Optional[dict]:
    prompt = []
    if spy_pct is not None:
        prompt.append(f"Market backdrop: S&P 500 {spy_pct:+.2f}% today.")
    prompt.append("Symbols (sorted by move size):")
    prompt.extend(f"- {l}" for l in lines)

    return await narrate(
        system_prompt=_SYSTEM_PROMPT,
        user_content="\n".join(prompt),
        agent_type="ledger_review",
        max_tokens=500,
        user_id=user_id,
        parser=_parse_review,
    )


def _parse_review(text: str) -> Optional[dict]:
    """Parse the model's {"title", "body"} — degrade to plain text, never drop
    a review over formatting."""
    if not text:
        return None
    candidate = text
    if candidate.startswith("```"):
        candidate = candidate.strip("`").lstrip("json").strip()
    match = re.search(r"\{.*\}", candidate, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group(0))
            title = str(parsed.get("title") or "").strip()
            body = str(parsed.get("body") or "").strip()
            if title:
                return {"title": title[:200], "body": body or None}
        except Exception:
            pass
    # Near-JSON: pull the field values out even if the syntax is broken.
    title_m = re.search(r'"title"\s*:\s*"([^"\n]+)', candidate, re.I)
    if title_m:
        body_m = re.search(r'"body"\s*:\s*"(.*?)("\s*[},]|$)', candidate, re.I | re.DOTALL)
        body = body_m.group(1).strip() if body_m else None
        return {"title": title_m.group(1).strip()[:200], "body": body or None}
    # Plain prose: first line is the takeaway, the rest is the body.
    lines = [l.strip() for l in candidate.splitlines() if l.strip().strip('{}"')]
    if not lines:
        return None
    return {"title": lines[0][:200], "body": "\n".join(lines[1:4]) or None}


async def _review_user(user_id: str, symbols: Dict[str, float],
                       quotes: Dict[str, dict], spy_pct: Optional[float],
                       day: str) -> bool:
    lines = _stat_lines(symbols, quotes)
    if not lines:
        return False
    narrated = await _narrate(lines, spy_pct, user_id)
    if not narrated:
        return False
    await emit_signal(
        user_id, "insight", narrated["title"], body=narrated["body"],
        data={"day": day, "symbols": list(symbols.keys())[:20]}, source="review",
    )
    return True


async def review_once(now_et: Optional[datetime] = None) -> int:
    """One sweep: review every eligible user not yet reviewed today."""
    now_et = now_et or datetime.now(ET)
    day = now_et.strftime("%Y-%m-%d")
    day_start_utc = now_et.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)

    users = await _gather_users()
    if not users:
        return 0
    done = await _reviewed_today(set(users.keys()), day_start_utc)
    todo = {u: s for u, s in users.items() if u not in done}
    # Heartbeat users get the agentic review instead — don't double-cover.
    from crud.user_preferences import get_user_preferences
    filtered = {}
    for uid, syms in todo.items():
        try:
            async with get_db_session() as db:
                prefs = await get_user_preferences(db, uid)
            if prefs.get("heartbeat_enabled"):
                continue
        except Exception:
            pass
        filtered[uid] = syms
    todo = filtered
    if not todo:
        return 0

    all_symbols = sorted(set().union(*(set(list(s.keys())[:MAX_SYMBOLS_PER_USER]) for s in todo.values())) | {"SPY"})
    quotes = await batch_quotes(all_symbols)
    if not quotes:
        return 0
    spy = quotes.get("SPY")
    spy_pct = float(spy["changesPercentage"]) if spy and spy.get("changesPercentage") is not None else None

    reviewed = 0
    for user_id, symbols in todo.items():
        if reviewed >= MAX_REVIEWS_PER_SWEEP:
            logger.warning("Ledger review sweep cap hit (%d)", MAX_REVIEWS_PER_SWEEP)
            break
        capped = dict(list(symbols.items())[:MAX_SYMBOLS_PER_USER])
        try:
            if await _review_user(user_id, capped, quotes, spy_pct, day):
                reviewed += 1
        except Exception:
            logger.exception("Ledger review failed for %s", user_id)
    return reviewed


async def run_ledger_review_loop() -> None:
    """After each weekday close, write the nightly review into every
    eligible user's ledger (once per day, DB-deduped)."""
    logger.info("Ledger review loop started")
    while True:
        try:
            if _in_review_window(datetime.now(ET)):
                n = await review_once()
                if n:
                    logger.info("Ledger review wrote %d insight(s)", n)
        except Exception:
            logger.exception("Ledger review loop error")
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
