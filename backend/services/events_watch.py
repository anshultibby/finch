"""
Corporate-events watch — the scheduled things investors told us they want
pushed, not just explained after the fact:

- Earnings heads-up: the trading day before a stock they own reports, with the
  consensus numbers and (if they wrote one) what their thesis says would make
  them wrong. Watchlist names get a ledger entry, not a push.
- Earnings recap: once the stock has traded on the report — beat/miss vs
  consensus, Finch's read of the reaction (noise / news / narrative shift), and
  a story check against their thesis, which is also logged to the thesis.
- Dividend changes: a raise or cut declared in the last few days.

Runs once per US trading day after the close. Every event carries a stable
`key` and is deduped against the ledger before any work is done, so a redeploy
(or a second instance) can't double-send.
"""
import asyncio
import logging
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

from sqlalchemy import select

from core.database import get_db_session
from services.monitoring.cache import TTLCache
from services.monitoring.inputs import symbols_by_user
from services.monitoring.sink import Push, emit_signal

logger = logging.getLogger(__name__)

ET = ZoneInfo("America/New_York")
SOURCE = "events"
RUN_AFTER_ET = (16, 45)
CHECK_INTERVAL_SECONDS = 15 * 60
DIVIDEND_LOOKBACK_DAYS = 3
DIVIDEND_CHANGE_MIN = 0.01  # ignore sub-1% rounding noise

SLOT = {"bmo": "before the open", "amc": "after the close", "dmh": "during market hours"}

_dividend_cache = TTLCache(ttl_seconds=12 * 3600, max_entries=5000)
_last_run_day: Optional[date] = None


# ── calendar helpers ─────────────────────────────────────────────────────────

def _next_trading_day(d: date) -> date:
    d += timedelta(days=1)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def _prev_trading_day(d: date) -> date:
    d -= timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def is_recap_due(entry: dict, today: date) -> bool:
    """The stock has traded a full session on this report by today's close."""
    if entry.get("eps") is None:
        return False
    when = entry.get("date")
    slot = (entry.get("time") or "").lower()
    if slot == "amc":
        return when == _prev_trading_day(today).isoformat()
    return when == today.isoformat()  # bmo / during hours report and react the same day


def is_heads_up_due(entry: dict, today: date) -> bool:
    return entry.get("date") == _next_trading_day(today).isoformat()


def classify_dividend(history: List[dict], today: date) -> Optional[dict]:
    """A raise/cut declared in the last few days vs the previous regular dividend."""
    regular = [
        h for h in history
        if (h.get("frequency") or "").lower() not in ("special", "irregular", "unknown")
        and (h.get("adjDividend") or h.get("dividend"))
    ]
    if len(regular) < 2:
        return None
    latest, prev = regular[0], regular[1]
    declared = latest.get("declarationDate")
    if not declared:
        return None
    try:
        declared_d = date.fromisoformat(declared[:10])
    except ValueError:
        return None
    if not (0 <= (today - declared_d).days <= DIVIDEND_LOOKBACK_DAYS):
        return None
    new = float(latest.get("adjDividend") or latest.get("dividend"))
    old = float(prev.get("adjDividend") or prev.get("dividend"))
    if old <= 0:
        return None
    change = new / old - 1
    if abs(change) < DIVIDEND_CHANGE_MIN:
        return None
    return {
        "kind": "raise" if change > 0 else "cut",
        "change_pct": round(change * 100, 1),
        "amount": round(new, 4),
        "previous": round(old, 4),
        "declared": declared[:10],
        "frequency": latest.get("frequency"),
    }


# ── data ─────────────────────────────────────────────────────────────────────

async def _earnings_window(today: date) -> Dict[str, List[dict]]:
    from skills.financial_modeling_prep.scripts.earnings.earnings_calendar import get_earnings_calendar

    start = _prev_trading_day(today).isoformat()
    end = _next_trading_day(today).isoformat()
    try:
        data = await asyncio.to_thread(get_earnings_calendar, start, end)
    except Exception:
        logger.exception("events watch: earnings calendar fetch failed")
        return {}
    by_symbol: Dict[str, List[dict]] = {}
    for e in data if isinstance(data, list) else []:
        if isinstance(e, dict) and e.get("symbol"):
            by_symbol.setdefault(e["symbol"].upper(), []).append(e)
    return by_symbol


async def _dividend_history(symbol: str) -> List[dict]:
    cached = _dividend_cache.get(symbol)
    if cached is not None:
        return cached
    from skills.financial_modeling_prep.scripts._client import call_fmp_stable_api

    try:
        data = await asyncio.to_thread(call_fmp_stable_api, "/dividends", {"symbol": symbol, "limit": 4})
    except Exception:
        return []
    if isinstance(data, dict):
        data = [] if data.get("error") else [data]
    history = [d for d in data if isinstance(d, dict)]
    _dividend_cache.set(symbol, history)
    return history


async def _already_sent(user_id: str, key: str) -> bool:
    from models.activity import AgentEvent

    async with get_db_session() as db:
        row = await db.execute(
            select(AgentEvent.id).where(
                AgentEvent.user_id == user_id,
                AgentEvent.source == SOURCE,
                AgentEvent.data["key"].astext == key,
            ).limit(1)
        )
        return row.first() is not None


def _usd(n) -> str:
    try:
        n = float(n)
    except (TypeError, ValueError):
        return "—"
    if abs(n) >= 1e9:
        return f"${n / 1e9:.1f}B"
    if abs(n) >= 1e6:
        return f"${n / 1e6:.0f}M"
    return f"${n:,.2f}"


# ── the three signals ────────────────────────────────────────────────────────

async def _earnings_heads_up(user_id: str, sym: str, e: dict, owned: bool) -> bool:
    from services.theses import get_thesis

    key = f"earn-pre:{sym}:{e['date']}"
    if await _already_sent(user_id, key):
        return False
    slot = SLOT.get((e.get("time") or "").lower(), "")
    title = f"{sym} reports tomorrow{(' ' + slot) if slot else ''}"
    parts = []
    if e.get("epsEstimated") is not None:
        est = f"Street expects EPS {_usd(e['epsEstimated'])}"
        if e.get("revenueEstimated"):
            est += f" on {_usd(e['revenueEstimated'])} revenue"
        parts.append(est + ".")
    thesis = await get_thesis(user_id, sym)
    if thesis and thesis.get("breaks"):
        parts.append(f"Your thesis says you'd be wrong if: {thesis['breaks'][:160]}")
    elif thesis and thesis.get("why"):
        parts.append(f"Your thesis: {thesis['why'][:160]}")
    else:
        parts.append("Tap for the setup: what matters, the implied move, and what it means for you.")
    body = " ".join(parts)
    await emit_signal(
        user_id, "alert", title, body=body, source=SOURCE,
        data={"key": key, "symbol": sym, "kind": "earnings_preview", "date": e["date"]},
        push=Push(title=title, body=body, notif_type="price", data={"symbol": sym}) if owned else None,
    )
    return True


async def _earnings_recap(user_id: str, sym: str, e: dict, owned: bool) -> bool:
    from services import theses
    from services.move_explainer import explain_move

    key = f"earn-post:{sym}:{e['date']}"
    if await _already_sent(user_id, key):
        return False

    eps, est = e.get("eps"), e.get("epsEstimated")
    if est is None:
        result_line = f"{sym} reported EPS {_usd(eps)}"
    else:
        word = "beat" if eps > est else "missed" if eps < est else "matched"
        result_line = f"{sym} {word}: EPS {_usd(eps)} vs {_usd(est)} expected"
    if e.get("revenue") and e.get("revenueEstimated"):
        result_line += f", revenue {_usd(e['revenue'])} vs {_usd(e['revenueEstimated'])}"

    try:
        read = await explain_move(sym)
    except Exception:
        logger.exception("events watch: explain_move failed for %s", sym)
        read = {}
    verdict = read.get("verdict") or "news"
    pct = read.get("change_pct")
    title = result_line + (f" · stock {pct:+.1f}%" if isinstance(pct, (int, float)) else "")

    body = read.get("explanation") or ""
    status = None
    thesis = await theses.get_thesis(user_id, sym)
    if thesis:
        check = await theses.check_against_thesis(
            user_id, thesis, f"Earnings: {result_line}. {theses.describe_read(read)}")
        if check:
            status = check["status"]
            body = f"{body}\nYour thesis: {status} — {check['reason']}".strip()
            await theses.log_story(user_id, sym, f"Earnings — {result_line}. {check['reason']}",
                                   verdict=verdict, status=status)

    label = {"noise": "Routine", "news": "News", "narrative_shift": "Story change"}.get(verdict, "News")
    if status in ("weakened", "broken"):
        label = f"Thesis {status}"
    push_title = f"{label}: {title}"[:140]
    should_push = owned or verdict != "noise" or status in ("weakened", "broken")
    await emit_signal(
        user_id, "alert", title, body=body, source=SOURCE,
        data={"key": key, "symbol": sym, "kind": "earnings_recap", "verdict": verdict,
              "driver": read.get("driver"), "thesis_status": status},
        push=Push(title=push_title, body=body[:180], notif_type="price", data={"symbol": sym}) if should_push else None,
    )
    return True


async def _dividend_change(user_id: str, sym: str, d: dict, owned: bool) -> bool:
    from services import theses

    key = f"div:{sym}:{d['declared']}"
    if await _already_sent(user_id, key):
        return False
    verb = "raised" if d["kind"] == "raise" else "cut"
    title = f"{sym} {verb} its dividend {abs(d['change_pct']):.1f}% to {_usd(d['amount'])}/share"
    body = f"Previous payout {_usd(d['previous'])}/share ({(d.get('frequency') or 'regular').lower()})."
    # A cut is the kind of change that rewrites an income thesis — check it.
    status = None
    thesis = await theses.get_thesis(user_id, sym)
    if thesis:
        check = await theses.check_against_thesis(user_id, thesis, f"Dividend: {title}. {body}")
        if check:
            status = check["status"]
            body += f"\nYour thesis: {status} — {check['reason']}"
            await theses.log_story(user_id, sym, f"{title}. {check['reason']}",
                                   verdict="narrative_shift" if d["kind"] == "cut" else "news", status=status)
    should_push = owned or d["kind"] == "cut"
    await emit_signal(
        user_id, "alert", title, body=body, source=SOURCE,
        data={"key": key, "symbol": sym, "kind": f"dividend_{d['kind']}", "thesis_status": status,
              "verdict": "narrative_shift" if d["kind"] == "cut" else "news"},
        push=Push(title=title, body=body[:180], notif_type="price", data={"symbol": sym}) if should_push else None,
    )
    return True


# ── the pass ─────────────────────────────────────────────────────────────────

async def run_once(today: Optional[date] = None) -> int:
    """One pass over every active user's owned + watched symbols. Returns signals sent."""
    today = today or datetime.now(ET).date()
    by_user = await symbols_by_user(require_device=False)
    if not by_user:
        return 0

    earnings = await _earnings_window(today)
    all_symbols = sorted(set().union(*({*v["owned"], *v["watched"]} for v in by_user.values())))
    histories = dict(zip(all_symbols, await asyncio.gather(*(_dividend_history(s) for s in all_symbols))))
    dividends = {s: classify_dividend(h, today) for s, h in histories.items()}

    sent = 0
    for user_id, groups in by_user.items():
        for sym in sorted(groups["owned"] | groups["watched"]):
            owned = sym in groups["owned"]
            try:
                for e in earnings.get(sym, []):
                    if is_heads_up_due(e, today):
                        sent += await _earnings_heads_up(user_id, sym, e, owned)
                    elif is_recap_due(e, today):
                        sent += await _earnings_recap(user_id, sym, e, owned)
                if dividends.get(sym):
                    sent += await _dividend_change(user_id, sym, dividends[sym], owned)
            except Exception:
                logger.exception("events watch failed for %s/%s", user_id, sym)
    return sent


async def run_events_watch_loop() -> None:
    global _last_run_day
    logger.info("Events watch started (runs weekdays after %02d:%02d ET)", *RUN_AFTER_ET)
    while True:
        try:
            now = datetime.now(ET)
            if now.weekday() < 5 and (now.hour, now.minute) >= RUN_AFTER_ET and _last_run_day != now.date():
                sent = await run_once(now.date())
                _last_run_day = now.date()
                logger.info("Events watch sent %d signal(s)", sent)
        except Exception:
            logger.exception("Events watch pass failed")
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
