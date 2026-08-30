"""
Market monitor — real-time smart alerts with the "why" attached.

During regular US market hours, watches the holdings + watchlist symbols of
every push-capable user. When a watched stock crosses a move threshold
(±5%, escalating at ±10%), sends a push notification whose body is the
AI-generated explanation of the move (via services.move_explainer, which is
cached and shared across users — N users watching NVDA cost one LLM call).

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

from sqlalchemy import select

from core.database import get_db_session
from services.insight_model import filter_active_users
from services.monitoring.inputs import batch_quotes, symbols_from_portfolio_data
from services.monitoring.sink import Push, emit_signal
from models.brokerage import PortfolioHoldingsCache, UserWatchlist
from models.user import DeviceToken

logger = logging.getLogger(__name__)

ET = ZoneInfo("America/New_York")

CHECK_INTERVAL_SECONDS = 15 * 60
ALERT_BANDS = (5.0, 10.0)  # abs % move thresholds, escalating
MAX_ALERTS_PER_USER_PER_DAY = 6

# (user_id, symbol, YYYY-MM-DD, band) already alerted
_alerted: Set[Tuple[str, str, str, float]] = set()
_alert_counts: Dict[Tuple[str, str], int] = {}  # (user_id, day) -> count


def _is_regular_session(now: datetime) -> bool:
    if now.weekday() >= 5:
        return False
    minutes = now.hour * 60 + now.minute
    return (9 * 60 + 30) <= minutes < (16 * 60)


async def _gather_user_symbols() -> Dict[str, Set[str]]:
    """Map of user_id -> watched symbols, for recently-active users with a device.

    A registered device is not evidence of a live user — tokens outlive the
    people who installed the app. Gating on recent activity too keeps the
    every-few-minutes sweep off dormant accounts.
    """
    async with get_db_session() as db:
        result = await db.execute(select(DeviceToken.user_id).distinct())
        user_ids = {row[0] for row in result.all()}
    user_ids = await filter_active_users(user_ids)
    if not user_ids:
        return {}

    async with get_db_session() as db:

        watched: Dict[str, Set[str]] = {uid: set() for uid in user_ids}

        result = await db.execute(
            select(UserWatchlist.user_id, UserWatchlist.symbol).where(
                UserWatchlist.user_id.in_(user_ids)
            )
        )
        for uid, sym in result.all():
            watched[uid].add(sym.upper())

        result = await db.execute(
            select(PortfolioHoldingsCache.user_id, PortfolioHoldingsCache.portfolio_data).where(
                PortfolioHoldingsCache.user_id.in_(user_ids)
            )
        )
        for uid, data in result.all():
            watched[uid].update(symbols_from_portfolio_data(data))

    return {uid: syms for uid, syms in watched.items() if syms}


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

    body = ""
    try:
        result = await explain_move(symbol)
        body = result.get("explanation") or ""
    except Exception:
        logger.exception("Alert explanation failed for %s", symbol)
    if not body:
        direction = "up" if pct >= 0 else "down"
        body = f"{quote.get('name') or symbol} is {direction} {abs(pct):.1f}% today."

    await emit_signal(
        user_id, "alert", title, body=body,
        data={"symbol": symbol, "pct": round(float(pct), 2)}, source="monitor",
        push=Push(title=title, body=body, notif_type="price", data={"symbol": symbol}),
    )


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
