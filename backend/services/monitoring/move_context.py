"""Deterministic context for judging a price move — the numbers every update
reasons from before an LLM writes a word.

Finch's updates are meant to be deliberate: for every move it mentions it should
say whether the move is routine for that stock, news that leaves the story
intact, or a genuine change in narrative, and whether the driver is macro,
sector or company-specific. Those calls are only as honest as their inputs, so
the inputs are measured here, not guessed by the model:

- how unusual the move is for *this* stock (|today| vs its own typical daily
  move over ~30 sessions — 5% is a big day for KO and a quiet one for a
  small-cap biotech);
- how much the market and the stock's sector explain (SPY + sector SPDR);
- volume vs average (conviction behind the move);
- whether earnings just landed or are imminent;
- a macro backdrop (indices, rates, dollar, oil, gold, volatility, sector
  leaders/laggards) plus the day's top market headlines.

`FRAMEWORK` is the shared rubric that the move explainer, the portfolio digest
and the agent prompts (morning brief, heartbeat, checks) all apply, so every
surface classifies moves the same way.
"""
import asyncio
import logging
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

from services.monitoring.cache import TTLCache
from services.monitoring.inputs import batch_quotes

logger = logging.getLogger(__name__)

SECTOR_ETF = {
    "Technology": "XLK",
    "Communication Services": "XLC",
    "Consumer Cyclical": "XLY",
    "Consumer Defensive": "XLP",
    "Financial Services": "XLF",
    "Healthcare": "XLV",
    "Industrials": "XLI",
    "Energy": "XLE",
    "Utilities": "XLU",
    "Real Estate": "XLRE",
    "Basic Materials": "XLB",
}

# Macro dashboard: what moves everything. ETFs stand in for rates/dollar/
# commodities because they quote reliably on the same endpoint as stocks.
MACRO = [
    ("SPY", "S&P 500"), ("QQQ", "Nasdaq 100"), ("IWM", "Russell 2000"),
    ("TLT", "Long Treasuries (up = yields down)"), ("UUP", "US dollar"),
    ("USO", "Oil"), ("GLD", "Gold"), ("^VIX", "VIX"),
]

FRAMEWORK = """How Finch judges a move (apply to every move you mention):

1. Is it unusual for THIS stock? Compare today's move to its typical daily move. Under ~1.5x typical is routine; 1.5-3x is notable; over 3x is a real event.
2. What drove it — macro, sector, or company?
   - Macro: the whole market moved (rates, Fed, inflation/jobs data, dollar, oil, geopolitics). If SPY explains most of it, say so.
   - Sector: peers and the sector ETF moved together (a read-through, rotation, sector news).
   - Company: the stock moved on its own (earnings, guidance, analyst action, product, legal/regulatory, management, deal).
3. Verdict — pick exactly one:
   - NOISE: routine for this stock, or explained by the market/sector with no company news. Nothing about the investment case changed.
   - NEWS, STORY INTACT: a real event (earnings beat/miss, upgrade, deal) that moves the price but fits the existing narrative — e.g. a sell-off on a good quarter from high expectations, or a one-off.
   - NARRATIVE SHIFT: the reason people own (or avoid) the stock has changed — guidance cut or raise that resets the growth path, a competitive threat, a regulatory or legal turn, a management change, a broken thesis. Reserve this; most days are not this.
4. Ground every claim in the headlines or numbers given. Never invent news. If the cause is unclear, say it's unclear and lean NOISE.
   Use dates and weekdays exactly as written in the input — never work out a weekday or "today/tomorrow" yourself. When markets are closed, the moves are from the last session: name it ("Friday's selloff"), don't call it "today".
5. End with what would confirm or change the call (the next print, a date, a level, a follow-up headline)."""

VERDICTS = ("noise", "news", "narrative_shift")
DRIVERS = ("macro", "sector", "company")

_typical_cache = TTLCache(ttl_seconds=6 * 3600, max_entries=2000)
_profile_cache = TTLCache(ttl_seconds=24 * 3600, max_entries=2000)
_macro_cache = TTLCache(ttl_seconds=10 * 60)


async def _typical_daily_move(symbol: str) -> Optional[float]:
    """Mean absolute daily % change over the last ~30 sessions."""
    cached = _typical_cache.get(symbol)
    if cached is not None:
        return cached or None
    from skills.financial_modeling_prep.scripts.api import fmp

    try:
        data = await asyncio.to_thread(fmp, f"/historical-price-full/{symbol}", {"timeseries": 31})
    except Exception:
        return None
    hist = (data or {}).get("historical") if isinstance(data, dict) else None
    closes = [h.get("close") for h in (hist or []) if isinstance(h, dict) and h.get("close")]
    # FMP returns newest first; daily % change between consecutive closes.
    changes = [abs(closes[i] / closes[i + 1] - 1) * 100 for i in range(len(closes) - 1) if closes[i + 1]]
    typical = round(sum(changes) / len(changes), 2) if len(changes) >= 10 else 0.0
    _typical_cache.set(symbol, typical)
    return typical or None


async def _sector(symbol: str) -> Optional[str]:
    cached = _profile_cache.get(symbol)
    if cached is not None:
        return cached or None
    from skills.financial_modeling_prep.scripts.api import fmp

    try:
        data = await asyncio.to_thread(fmp, f"/profile/{symbol}")
    except Exception:
        return None
    if isinstance(data, list):
        data = data[0] if data else {}
    sector = (data or {}).get("sector") or ""
    _profile_cache.set(symbol, sector)
    return sector or None


async def macro_backdrop() -> Dict:
    """Shared, cached snapshot: macro tape, sector leaders/laggards, top headlines."""
    cached = _macro_cache.get("macro")
    if cached is not None:
        return cached
    from skills.financial_modeling_prep.scripts._client import call_fmp_stable_api

    async with _macro_cache.lock("macro"):
        cached = _macro_cache.get("macro")
        if cached is not None:
            return cached
        symbols = [s for s, _ in MACRO] + list(SECTOR_ETF.values())
        quotes, news = await asyncio.gather(
            batch_quotes(symbols),
            # General (macro/market) news, not the ticker feed — that one is
            # mostly law-firm spam and fund reviews.
            asyncio.to_thread(call_fmp_stable_api, "/news/general-latest", {"limit": 12}),
            return_exceptions=True,
        )
        quotes = quotes if isinstance(quotes, dict) else {}
        tape = [
            {"symbol": s, "label": label, "change_pct": round(float(quotes[s]["changesPercentage"]), 2)}
            for s, label in MACRO
            if s in quotes and quotes[s].get("changesPercentage") is not None
        ]
        sectors = sorted(
            (
                {"sector": name, "etf": etf, "change_pct": round(float(quotes[etf]["changesPercentage"]), 2)}
                for name, etf in SECTOR_ETF.items()
                if etf in quotes and quotes[etf].get("changesPercentage") is not None
            ),
            key=lambda x: x["change_pct"], reverse=True,
        )
        headlines = [
            n["title"] for n in (news if isinstance(news, list) else [])
            if isinstance(n, dict) and n.get("title")
        ][:8]
        result = {"tape": tape, "sectors": sectors, "headlines": headlines}
        if tape:
            _macro_cache.set("macro", result)
        return result


def macro_lines(backdrop: Dict) -> List[str]:
    """Render the backdrop as prompt lines."""
    lines = [session_line()]
    if backdrop.get("tape"):
        lines.append("Macro tape today: " + "; ".join(
            f"{t['label']} {t['change_pct']:+.2f}%" for t in backdrop["tape"]))
    secs = backdrop.get("sectors") or []
    if len(secs) >= 4:
        lines.append("Sector leaders: " + ", ".join(f"{s['sector']} {s['change_pct']:+.2f}%" for s in secs[:2])
                     + " | laggards: " + ", ".join(f"{s['sector']} {s['change_pct']:+.2f}%" for s in secs[-2:]))
    if backdrop.get("headlines"):
        lines.append("Top market headlines:")
        lines.extend(f"- {h}" for h in backdrop["headlines"][:6])
    return lines


ET = ZoneInfo("America/New_York")


def _last_session(d: date) -> date:
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def session_line(now: Optional[datetime] = None) -> str:
    """Where we are in the trading week, stated so the model never guesses it.
    Holidays aren't modelled."""
    now = now or datetime.now(ET)
    today = now.date()
    stamp = f"{now:%A}, {now:%b} {today.day}"
    mins = now.hour * 60 + now.minute
    if today.weekday() < 5 and 570 <= mins < 960:
        return f"Now: {stamp}, {now:%-I:%M %p} ET. Markets are open — moves are intraday."
    if today.weekday() < 5 and mins >= 960:
        return f"Now: {stamp}, after the close. Moves are today's ({now:%A}'s) session."
    last = _last_session(today - timedelta(days=1)) if (today.weekday() >= 5 or mins < 570) else today
    return (f"Now: {stamp}. Markets are closed; moves shown are from the last session, "
            f"{last:%A} {last:%b} {last.day}.")


def _earnings_note(quote: dict) -> Optional[str]:
    raw = quote.get("earningsAnnouncement")
    if not raw:
        return None
    try:
        when = datetime.fromisoformat(str(raw).replace("Z", "+00:00")).date()
    except ValueError:
        return None
    days = (when - date.today()).days
    # Weekday spelled out so no model ever has to compute it.
    label = f"{when:%A} {when:%b} {when.day}"
    if days == 0:
        return f"Earnings today ({label})"
    if -3 <= days < 0:
        return f"Reported earnings {-days} day{'s' if days < -1 else ''} ago ({label})"
    if 0 < days <= 7:
        return f"Earnings in {days} day{'s' if days > 1 else ''} ({label})"
    return None


async def move_context(symbol: str, quote: dict, backdrop: Optional[Dict] = None) -> Dict:
    """Measured context for one symbol's move today. Never raises; fields may be None."""
    sym = symbol.upper()
    pct = float(quote.get("changesPercentage") or 0.0)
    typical, sector = await asyncio.gather(_typical_daily_move(sym), _sector(sym))
    backdrop = backdrop or await macro_backdrop()

    spy = next((t["change_pct"] for t in backdrop.get("tape", []) if t["symbol"] == "SPY"), None)
    etf = SECTOR_ETF.get(sector or "")
    sector_pct = next((s["change_pct"] for s in backdrop.get("sectors", []) if s["etf"] == etf), None)

    vol_ratio = None
    try:
        if quote.get("volume") and quote.get("avgVolume"):
            vol_ratio = round(float(quote["volume"]) / float(quote["avgVolume"]), 1)
    except (TypeError, ValueError, ZeroDivisionError):
        pass

    multiple = round(abs(pct) / typical, 1) if typical else None
    # A prior for the model, not the verdict: how much is left once the
    # sector (or the market, if sector is unknown) is taken out.
    bench = sector_pct if sector_pct is not None else spy
    idiosyncratic = round(pct - bench, 2) if bench is not None else None
    if multiple is not None and multiple < 1.5:
        prior = "routine for this stock"
    elif idiosyncratic is not None and abs(idiosyncratic) < max(1.0, (typical or 1.0)):
        prior = "mostly explained by the market/sector"
    else:
        prior = "stock-specific"

    return {
        "symbol": sym,
        "change_pct": round(pct, 2),
        "typical_move_pct": typical,
        "move_multiple": multiple,
        "sector": sector,
        "sector_etf": etf,
        "sector_change_pct": sector_pct,
        "spy_change_pct": spy,
        "idiosyncratic_pct": idiosyncratic,
        "volume_ratio": vol_ratio,
        "earnings": _earnings_note(quote),
        "prior": prior,
    }


def context_lines(ctx: Dict) -> List[str]:
    """Render one symbol's measured context as prompt lines."""
    lines = []
    if ctx.get("typical_move_pct"):
        lines.append(f"Typical daily move for {ctx['symbol']}: ±{ctx['typical_move_pct']:.2f}% "
                     f"→ today is {ctx['move_multiple']}x typical.")
    parts = []
    if ctx.get("spy_change_pct") is not None:
        parts.append(f"S&P 500 {ctx['spy_change_pct']:+.2f}%")
    if ctx.get("sector_change_pct") is not None:
        parts.append(f"its sector ({ctx['sector']}, {ctx['sector_etf']}) {ctx['sector_change_pct']:+.2f}%")
    if parts:
        lines.append("Benchmarks: " + ", ".join(parts)
                     + (f" → {ctx['idiosyncratic_pct']:+.2f}% is stock-specific." if ctx.get("idiosyncratic_pct") is not None else "."))
    if ctx.get("volume_ratio"):
        lines.append(f"Volume is {ctx['volume_ratio']}x average.")
    if ctx.get("earnings"):
        lines.append(ctx["earnings"])
    lines.append(f"Measured prior: {ctx['prior']}.")
    return lines
