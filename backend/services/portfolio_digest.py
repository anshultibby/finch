"""
Portfolio "Today" digest — a generated daily narrative of what the user's
portfolio (or watchlist, if no brokerage is connected) did today and why.

The numbers are computed deterministically from quotes (per-holding day P&L
contribution = shares x today's $ change); the LLM only narrates them, grounded
in headlines for the top movers. Cached per user for 10 minutes.
"""
import asyncio
import csv
import io
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select

from core.constants import Models
from core.database import get_db_session
from models.brokerage import UserWatchlist

logger = logging.getLogger(__name__)

DIGEST_MODEL = Models.GLM_5_1

_CACHE_TTL_SECONDS = 10 * 60
_cache: Dict[str, Dict[str, Any]] = {}
_locks: Dict[str, asyncio.Lock] = {}

_SYSTEM_PROMPT = """You write the short "Today" story for a person's portfolio in a finance app. You get computed numbers (already correct — never recompute or contradict them) plus headlines for the biggest movers.

Rules:
- 2-3 sentences, plain conversational English, like a smart friend summarizing their day.
- Lead with what drove the day: name the 1-2 holdings that mattered most and why (from headlines, if they explain it; otherwise the broad market).
- Mention the market backdrop only if it explains the move.
- Don't restate the total portfolio change — the user sees the number right above your text. Don't use bullet points, headers, or emojis. Never invent news.
- If this is a watchlist (not owned positions), talk about "your watchlist" naturally."""


def _parse_holdings(holdings_csv: str) -> List[dict]:
    holdings = []
    for row in csv.DictReader(io.StringIO(holdings_csv)):
        try:
            holdings.append({
                "symbol": (row.get("symbol") or "").upper(),
                "quantity": float(row.get("quantity") or 0),
                "value": float(row.get("value") or 0),
            })
        except (ValueError, TypeError):
            continue
    return [h for h in holdings if h["symbol"] and h["value"] > 0]


async def _watchlist_symbols(user_id: str) -> List[str]:
    async with get_db_session() as db:
        result = await db.execute(
            select(UserWatchlist.symbol).where(UserWatchlist.user_id == user_id).distinct()
        )
        return [s.upper() for (s,) in result.all()]


async def _batch_quotes(symbols: List[str]) -> Dict[str, dict]:
    from skills.financial_modeling_prep.scripts.api import fmp

    quotes: Dict[str, dict] = {}
    # FMP handles long symbol lists, but chunk defensively.
    for i in range(0, len(symbols), 50):
        chunk = ",".join(symbols[i:i + 50])
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


async def get_portfolio_digest(user_id: str) -> Dict[str, Any]:
    cached = _cache.get(user_id)
    if cached and (time.monotonic() - cached["at"]) < _CACHE_TTL_SECONDS:
        return cached["result"]

    lock = _locks.setdefault(user_id, asyncio.Lock())
    async with lock:
        cached = _cache.get(user_id)
        if cached and (time.monotonic() - cached["at"]) < _CACHE_TTL_SECONDS:
            return cached["result"]
        result = await _build_digest(user_id)
        # Don't cache failures or empty states — the user may connect/add
        # symbols and expect the card to appear right away.
        if result.get("success") and result.get("mode") != "empty":
            _cache[user_id] = {"at": time.monotonic(), "result": result}
        return result


async def _build_digest(user_id: str) -> Dict[str, Any]:
    from modules.tools.clients import snaptrade_tools

    holdings: List[dict] = []
    mode = "watchlist"
    try:
        portfolio = await snaptrade_tools.get_portfolio(user_id)
        if portfolio.get("success"):
            holdings = _parse_holdings(portfolio.get("holdings_csv", ""))
            if holdings:
                mode = "portfolio"
    except Exception:
        logger.exception("Digest: portfolio fetch failed for %s", user_id)

    if mode == "watchlist":
        symbols = await _watchlist_symbols(user_id)
        if not symbols:
            return {"success": True, "mode": "empty"}
        holdings = [{"symbol": s, "quantity": 0.0, "value": 0.0} for s in symbols[:30]]

    quotes = await _batch_quotes([h["symbol"] for h in holdings])
    spy_quotes = await _batch_quotes(["SPY"])
    spy = spy_quotes.get("SPY")

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

    narrative = await _generate_narrative(mode, day_change_total, day_change_pct, top, spy)

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
    mode: str,
    day_change: float,
    day_change_pct: float,
    top_movers: List[dict],
    spy: Optional[dict],
) -> str:
    from modules.agent.llm_handler import LLMHandler

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

    handler = LLMHandler(user_id=None, chat_id=None, agent_type="portfolio_digest")
    try:
        response = await handler.acompletion(
            model=DIGEST_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": "\n".join(lines)},
            ],
            stream=False,
            max_tokens=1000,
            # Disable GLM's default server-side reasoning — it adds ~30s of
            # latency and a short narration task doesn't need it.
            extra_body={"thinking": {"type": "disabled"}},
        )
        text = (response.choices[0].message.content or "").strip()
        if text:
            return text
    except Exception:
        logger.exception("Digest narrative LLM call failed")

    leader = top_movers[0]
    return (
        f"{leader['name']} was the biggest mover today at {leader['change_pct']:+.2f}%."
    )
