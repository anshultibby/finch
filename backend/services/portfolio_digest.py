"""
Portfolio "Today" digest — a generated daily narrative of what the user's
portfolio (or watchlist, if no brokerage is connected) did today and why.

The numbers are computed deterministically from quotes (per-holding day P&L
contribution = shares x today's $ change); the LLM only narrates them, grounded
in headlines for the top movers. Cached per user for 10 minutes.
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from services.monitoring.cache import TTLCache
from services.monitoring.inputs import (
    batch_quotes,
    parse_holdings,
    spy_backdrop,
    watchlist_symbols,
)
from services.monitoring.narrate import narrate

logger = logging.getLogger(__name__)

# Model is resolved per user (see services.insight_model): this path sends the
# user's actual holdings, so GLM is opt-in per tenant and off by default.

_digest_cache = TTLCache(ttl_seconds=10 * 60)

_SYSTEM_PROMPT = """You write the short "Today" story for a person's portfolio in a finance app. You get computed numbers (already correct — never recompute or contradict them) plus headlines for the biggest movers.

Rules:
- 2-3 sentences, plain conversational English, like a smart friend summarizing their day.
- Lead with what drove the day: name the 1-2 holdings that mattered most and why (from headlines, if they explain it; otherwise the broad market).
- Mention the market backdrop only if it explains the move.
- Don't restate the total portfolio change — the user sees the number right above your text. Don't use bullet points, headers, or emojis. Never invent news.
- If this is a watchlist (not owned positions), talk about "your watchlist" naturally."""


async def get_portfolio_digest(user_id: str) -> Dict[str, Any]:
    cached = _digest_cache.get(user_id)
    if cached is not None:
        return cached

    async with _digest_cache.lock(user_id):
        cached = _digest_cache.get(user_id)
        if cached is not None:
            return cached
        result = await _build_digest(user_id)
        # Don't cache failures or empty states — the user may connect/add
        # symbols and expect the card to appear right away.
        if result.get("success") and result.get("mode") != "empty":
            _digest_cache.set(user_id, result)
        return result


async def _build_digest(user_id: str) -> Dict[str, Any]:
    from modules.tools.clients import snaptrade_tools

    holdings: List[dict] = []
    mode = "watchlist"
    try:
        portfolio = await snaptrade_tools.get_portfolio(user_id)
        if portfolio.get("success"):
            holdings = parse_holdings(portfolio.get("holdings_csv", ""))
            if holdings:
                mode = "portfolio"
    except Exception:
        logger.exception("Digest: portfolio fetch failed for %s", user_id)

    if mode == "watchlist":
        symbols = await watchlist_symbols(user_id)
        if not symbols:
            return {"success": True, "mode": "empty"}
        holdings = [{"symbol": s, "quantity": 0.0, "value": 0.0} for s in symbols[:30]]

    quotes = await batch_quotes([h["symbol"] for h in holdings])
    spy = await spy_backdrop()

    movers = []
    day_change_total = 0.0
    total_value = 0.0
    for h in holdings:
        q = quotes.get(h["symbol"])
        if not q or q.get("changesPercentage") is None:
            continue
        change = float(q.get("change") or 0)
        contribution = h["quantity"] * change if mode == "portfolio" else 0.0
        day_change_total += contribution
        total_value += h["value"]
        movers.append({
            "symbol": h["symbol"],
            "name": q.get("name") or h["symbol"],
            "change_pct": round(float(q["changesPercentage"]), 2),
            "change": round(change, 2),
            "contribution": round(contribution, 2),
            "value": round(h["value"], 2),
        })

    if not movers:
        return {"success": True, "mode": "empty"}

    sort_key = (lambda m: abs(m["contribution"])) if mode == "portfolio" else (lambda m: abs(m["change_pct"]))
    movers.sort(key=sort_key, reverse=True)
    top = movers[:5]

    prev_value = total_value - day_change_total
    day_change_pct = (day_change_total / prev_value * 100) if prev_value > 0 else 0.0

    narrative = await _generate_narrative(
        user_id, mode, day_change_total, day_change_pct, top, spy
    )

    result = {
        "success": True,
        "mode": mode,
        "total_value": round(total_value, 2),
        "day_change": round(day_change_total, 2),
        "day_change_pct": round(day_change_pct, 2),
        "movers": top,
        "narrative": narrative,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    return result


async def _fetch_headlines(symbol: str, limit: int = 3) -> List[str]:
    from skills.financial_modeling_prep.scripts.api import fmp

    try:
        data = await asyncio.to_thread(fmp, f"/stock_news?tickers={symbol}&limit={limit}")
    except Exception:
        return []
    if not isinstance(data, list):
        return []
    return [n["title"] for n in data if isinstance(n, dict) and n.get("title")]


async def _generate_narrative(
    user_id: str,
    mode: str,
    day_change: float,
    day_change_pct: float,
    top_movers: List[dict],
    spy: Optional[dict],
) -> str:
    lines = []
    if mode == "portfolio":
        lines.append(
            f"Portfolio day change: ${day_change:+,.2f} ({day_change_pct:+.2f}%)."
        )
    else:
        lines.append("This is the user's watchlist (they don't own these via a connected account).")

    if spy and spy.get("changesPercentage") is not None:
        lines.append(f"Market backdrop: S&P 500 {spy['changesPercentage']:+.2f}% today.")

    lines.append("\nBiggest movers:")
    headline_lists = await asyncio.gather(
        *(_fetch_headlines(m["symbol"]) for m in top_movers[:3])
    )
    headlines_by_symbol = dict(zip((m["symbol"] for m in top_movers[:3]), headline_lists))
    for m in top_movers:
        line = f"- {m['name']} ({m['symbol']}): {m['change_pct']:+.2f}%"
        if mode == "portfolio" and m["contribution"]:
            line += f", contributing ${m['contribution']:+,.2f} to the day"
        lines.append(line)
        for h in headlines_by_symbol.get(m["symbol"], [])[:3]:
            lines.append(f"    headline: {h}")

    lines.append("\nWrite the 2-3 sentence 'Today' story.")

    text = await narrate(
        system_prompt=_SYSTEM_PROMPT,
        user_content="\n".join(lines),
        agent_type="portfolio_digest",
        max_tokens=1000,
        user_id=user_id,
    )
    if text:
        return text

    leader = top_movers[0]
    return (
        f"{leader['name']} was the biggest mover today at {leader['change_pct']:+.2f}%."
    )
