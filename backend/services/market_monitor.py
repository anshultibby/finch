"""
Market monitor — real-time smart alerts with the "why" attached.

During regular US market hours, watches the holdings + watchlist symbols of
every push-capable user. When a watched stock crosses a move threshold
(±5%, escalating at ±10%), it classifies the move via services.move_explainer
(cached and shared across users — N users watching NVDA cost one LLM call):
routine moves are logged to the ledger without a push; news and narrative
shifts push with the explanation as the body.

Design choices for v1:
- Holdings symbols come from the last PortfolioHoldingsCache row even if it's
  stale: we only need the symbol list, not fresh share counts, and this avoids
  hammering SnapTrade every cycle.
- Alert dedup state is in-memory, keyed (user, symbol, day, band) — fine for a
  single-instance deploy; worst case after a restart a user gets one repeat.
- Hard cap per user per day so a wild market day never becomes spam.
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, Set, Tuple
from zoneinfo import ZoneInfo

from core.database import get_db_session
from services.monitoring.inputs import batch_quotes, symbols_by_user
from services.monitoring.sink import Push, emit_signal

logger = logging.getLogger(__name__)

ET = ZoneInfo("America/New_York")

CHECK_INTERVAL_SECONDS = 15 * 60
ALERT_BANDS = (5.0, 10.0)  # abs % move thresholds, escalating
MAX_ALERTS_PER_USER_PER_DAY = 6

VERDICT_LABEL = {"noise": "Routine", "news": "News", "narrative_shift": "Story change"}

# (user_id, symbol, YYYY-MM-DD, band) already alerted
_alerted: Set[Tuple[str, str, str, float]] = set()
_alert_counts: Dict[Tuple[str, str], int] = {}  # (user_id, day) -> count


def _is_regular_session(now: datetime) -> bool:
    if now.weekday() >= 5:
        return False
    minutes = now.hour * 60 + now.minute
    return (9 * 60 + 30) <= minutes < (16 * 60)


async def _gather_user_symbols() -> Dict[str, Set[str]]:
    """Map of user_id -> watched symbols, for recently-active users with a device."""
    by_user = await symbols_by_user(require_device=True)
    return {uid: v["owned"] | v["watched"] for uid, v in by_user.items()}


def _crossed_band(pct: float) -> float | None:
    """Highest alert band that abs(pct) has crossed, or None."""
    crossed = None
    for band in ALERT_BANDS:
        if abs(pct) >= band:
            crossed = band
    return crossed


async def _heartbeat_enabled(user_id: str) -> bool:
    try:
        from crud.user_preferences import get_user_preferences
        async with get_db_session() as db:
            prefs = await get_user_preferences(db, user_id)
        return bool(prefs.get("heartbeat_enabled"))
    except Exception:
        return False


async def _send_alert(user_id: str, symbol: str, quote: dict) -> None:
    from services.move_explainer import explain_move

    pct = quote.get("changesPercentage") or 0.0
    arrow = "▲" if pct >= 0 else "▼"
    title = f"{symbol} {arrow} {abs(pct):.1f}%"

    # Heartbeat users get ONE source of alerts: the tripwire wakes their
    # heartbeat agent, which investigates and decides whether to alert
    # (report_insight). Everyone else keeps the direct templated push.
    if await _heartbeat_enabled(user_id):
        from services.system_jobs import trigger_heartbeat_now
        await trigger_heartbeat_now(user_id, f"{symbol} moved {pct:+.1f}% today")
        return

    body, verdict, driver, result = "", "news", None, {}
    try:
        result = await explain_move(symbol)
        body = result.get("explanation") or ""
        verdict = result.get("verdict") or "news"
        driver = result.get("driver")
        if result.get("headline"):
            title = f"{title} · {result['headline']}"[:120]
    except Exception:
        logger.exception("Alert explanation failed for %s", symbol)
    if not body:
        direction = "up" if pct >= 0 else "down"
        body = f"{quote.get('name') or symbol} is {direction} {abs(pct):.1f}% today."

    # Judge anything that isn't routine against the user's own thesis, if they
    # wrote one, and log it to the thesis's story — that's what turns an alert
    # into "does this change why I own it?".
    thesis_status = None
    if verdict != "noise" and result:
        thesis_status, thesis_line = await _thesis_check(user_id, symbol, result)
        if thesis_line:
            body = f"{body}\n{thesis_line}"

    # Deliberate, not noisy: a move that's routine for this stock (or just the
    # market/sector) is logged to the ledger but doesn't buzz the phone. A
    # narrative shift is called out as such in the push.
    label = VERDICT_LABEL.get(verdict, "")
    push = None
    if verdict != "noise":
        if thesis_status in ("weakened", "broken"):
            label = f"Thesis {thesis_status}"
        push = Push(
            title=f"{label}: {title}" if verdict == "narrative_shift" or thesis_status in ("weakened", "broken") else title,
            body=body, notif_type="price", data={"symbol": symbol},
        )

    await emit_signal(
        user_id, "alert", title, body=body,
        data={"symbol": symbol, "pct": round(float(pct), 2), "verdict": verdict, "driver": driver,
              "thesis_status": thesis_status},
        source="monitor", push=push,
    )


async def _thesis_check(user_id: str, symbol: str, read: dict) -> Tuple[str | None, str | None]:
    """(status, one-line summary) of a move against the user's thesis, or (None, None)."""
    from services import theses
    try:
        t = await theses.get_thesis(user_id, symbol)
        if not t:
            return None, None
        check = await theses.check_against_thesis(user_id, t, theses.describe_read(read))
        if not check:
            return None, None
        await theses.log_story(
            user_id, symbol, f"{read.get('headline') or read.get('explanation', '')[:160]} — {check['reason']}",
            verdict=read.get("verdict") or "news", status=check["status"],
        )
        return check["status"], f"Your thesis: {check['status']} — {check['reason']}"
    except Exception:
        logger.exception("Thesis check failed for %s/%s", user_id, symbol)
        return None, None


async def check_once() -> int:
    """Run one monitor pass. Returns the number of alerts sent."""
    watched = await _gather_user_symbols()
    if not watched:
        return 0

    all_symbols = sorted(set().union(*watched.values()))
    quotes = await batch_quotes(all_symbols, chunk_size=100)
    if not quotes:
        return 0

    day = datetime.now(ET).strftime("%Y-%m-%d")
    sent = 0
    for user_id, symbols in watched.items():
        if _alert_counts.get((user_id, day), 0) >= MAX_ALERTS_PER_USER_PER_DAY:
            continue
        for symbol in symbols:
            quote = quotes.get(symbol)
            if not quote or quote.get("changesPercentage") is None:
                continue
            band = _crossed_band(float(quote["changesPercentage"]))
            if band is None:
                continue
            key = (user_id, symbol, day, band)
            if key in _alerted:
                continue
            _alerted.add(key)
            # Crossing 10% also implies 5% — suppress the lower band so a
            # single check doesn't double-fire for the same symbol.
            for lower in ALERT_BANDS:
                if lower < band:
                    _alerted.add((user_id, symbol, day, lower))
            await _send_alert(user_id, symbol, quote)
            sent += 1
            _alert_counts[(user_id, day)] = _alert_counts.get((user_id, day), 0) + 1
            if _alert_counts[(user_id, day)] >= MAX_ALERTS_PER_USER_PER_DAY:
                break

    # Prune state from previous days.
    stale = [k for k in _alerted if k[2] != day]
    for k in stale:
        _alerted.discard(k)
    for k in [k for k in _alert_counts if k[1] != day]:
        _alert_counts.pop(k, None)

    return sent


async def run_market_monitor_loop() -> None:
    logger.info("Market monitor started (bands: %s, interval: %ss)", ALERT_BANDS, CHECK_INTERVAL_SECONDS)
    while True:
        try:
            if _is_regular_session(datetime.now(ET)):
                sent = await check_once()
                if sent:
                    logger.info("Market monitor sent %d alert(s)", sent)
        except Exception:
            logger.exception("Market monitor pass failed")
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
