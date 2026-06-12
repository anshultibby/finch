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
import csv
import io
import logging
from datetime import datetime
from typing import Dict, List, Set, Tuple
from zoneinfo import ZoneInfo

from sqlalchemy import select

from core.database import get_db_session
from models.brokerage import PortfolioHoldingsCache, UserWatchlist
from models.user import DeviceToken

logger = logging.getLogger(__name__)

ET = ZoneInfo("America/New_York")

CHECK_INTERVAL_SECONDS = 5 * 60
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


def _symbols_from_cached_portfolio(portfolio_data: dict) -> List[str]:
    holdings_csv = (portfolio_data or {}).get("holdings_csv") or ""
    symbols = []
    try:
        for row in csv.DictReader(io.StringIO(holdings_csv)):
            sym = (row.get("symbol") or "").upper().strip()
            if sym:
                symbols.append(sym)
    except Exception:
        return []
    return symbols


async def _gather_user_symbols() -> Dict[str, Set[str]]:
    """Map of user_id -> watched symbols, for users with a registered device."""
    async with get_db_session() as db:
        result = await db.execute(select(DeviceToken.user_id).distinct())
        user_ids = {row[0] for row in result.all()}
        if not user_ids:
            return {}

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
            watched[uid].update(_symbols_from_cached_portfolio(data))

    return {uid: syms for uid, syms in watched.items() if syms}


async def _fetch_quotes(symbols: List[str]) -> Dict[str, dict]:
    from skills.financial_modeling_prep.scripts.api import fmp

    quotes: Dict[str, dict] = {}
    for i in range(0, len(symbols), 100):
        chunk = ",".join(symbols[i:i + 100])
        try:
            data = await asyncio.to_thread(fmp, f"/quote/{chunk}")
        except Exception:
            continue
        if isinstance(data, dict):
            data = [data]
        if isinstance(data, list):
            for q in data:
                if isinstance(q, dict) and q.get("symbol"):
                    quotes[q["symbol"].upper()] = q
    return quotes


def _crossed_band(pct: float) -> float | None:
    """Highest alert band that abs(pct) has crossed, or None."""
    crossed = None
    for band in ALERT_BANDS:
        if abs(pct) >= band:
            crossed = band
    return crossed


async def _send_alert(user_id: str, symbol: str, quote: dict) -> None:
    from services.move_explainer import explain_move
    from services.push_notifications import send_push_notification

    pct = quote.get("changesPercentage") or 0.0
    arrow = "▲" if pct >= 0 else "▼"
    title = f"{symbol} {arrow} {abs(pct):.1f}%"

    body = ""
    try:
        result = await explain_move(symbol)
        body = result.get("explanation") or ""
    except Exception:
        logger.exception("Alert explanation failed for %s", symbol)
    if not body:
        direction = "up" if pct >= 0 else "down"
        body = f"{quote.get('name') or symbol} is {direction} {abs(pct):.1f}% today."

    async with get_db_session() as db:
        await send_push_notification(
            db,
            user_id,
            title=title,
            body=body,
            data={"symbol": symbol},
            notif_type="price",
        )


async def check_once() -> int:
    """Run one monitor pass. Returns the number of alerts sent."""
    watched = await _gather_user_symbols()
    if not watched:
        return 0

    all_symbols = sorted(set().union(*watched.values()))
    quotes = await _fetch_quotes(all_symbols)
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
