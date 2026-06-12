"""
Move Explainer — instant, grounded "why is this moving?" intelligence.

Given a symbol, fetches today's quote + recent headlines (FMP) plus the S&P 500
move for market context, and asks a fast model for a 1-2 sentence plain-English
explanation. Results are cached in-memory per symbol and shared across all
users (the explanation of why NVDA is up today is the same for everyone), so
the marginal cost of the feature stays near zero.

The cache invalidates when the price has moved materially since the cached
explanation was generated — an explanation of "+2% on analyst upgrade" should
not survive the stock swinging to -4%.
"""
import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

from core.constants import Models

logger = logging.getLogger(__name__)

EXPLAINER_MODEL = Models.GLM_5_1

# Cache entries live this long, and are also dropped if the live change% has
# drifted more than _CACHE_DRIFT_PCT points from when the entry was generated.
_CACHE_TTL_SECONDS = 20 * 60
_CACHE_DRIFT_PCT = 1.0

_cache: Dict[str, Dict[str, Any]] = {}
# Per-symbol locks so a burst of requests for the same symbol generates once.
_locks: Dict[str, asyncio.Lock] = {}

_SYSTEM_PROMPT = """You are a sharp, honest markets analyst. Explain in 1-2 short sentences why a stock is moving today, for a regular person checking their phone.

Rules:
- Ground the explanation in the provided headlines when they clearly explain the move. Never invent news.
- If the headlines don't explain it, say what's most plausible (sector rotation, broad market move, earnings drift, profit-taking) and frame it as likely, not certain.
- Use the market context: if the whole market moved similarly, say it's mostly a market-wide move.
- Plain English. No jargon, no hedging boilerplate, no "as an AI". Don't repeat the price or percentage — the user already sees those.
- Maximum 2 sentences."""


def _quote_fields(q: dict) -> dict:
    return {
        "symbol": q.get("symbol"),
        "name": q.get("name") or "",
        "price": q.get("price"),
        "change": q.get("change"),
        "change_pct": q.get("changesPercentage"),
    }


async def _fetch_quote(symbol: str) -> Optional[dict]:
    from skills.financial_modeling_prep.scripts.market.quote import get_quote_snapshot

    try:
        data = await asyncio.to_thread(get_quote_snapshot, symbol)
    except Exception:
        return None
    if isinstance(data, list) and data:
        return data[0]
    if isinstance(data, dict) and data.get("symbol"):
        return data
    return None


async def _fetch_news(symbol: str, limit: int = 8) -> List[dict]:
    from skills.financial_modeling_prep.scripts.api import fmp

    try:
        data = await asyncio.to_thread(
            fmp, f"/stock_news?tickers={symbol}&limit={limit}"
        )
    except Exception:
        return []
    return data if isinstance(data, list) else []


async def explain_move(symbol: str) -> Dict[str, Any]:
    """Return {symbol, name, price, change_pct, explanation, sources, as_of}.

    Raises ValueError if no quote exists for the symbol.
    """
    sym = symbol.upper().strip()

    quote = await _fetch_quote(sym)
    if not quote:
        raise ValueError(f"No quote found for {sym}")
    change_pct = quote.get("changesPercentage") or 0.0

    cached = _cache.get(sym)
    if cached:
        fresh = (time.monotonic() - cached["at"]) < _CACHE_TTL_SECONDS
        stable = abs((cached["change_pct"] or 0.0) - change_pct) < _CACHE_DRIFT_PCT
        if fresh and stable:
            return {**cached["result"], **_quote_fields(quote), "cached": True}

    lock = _locks.setdefault(sym, asyncio.Lock())
    async with lock:
        # Re-check under the lock — another request may have just generated it.
        cached = _cache.get(sym)
        if cached and (time.monotonic() - cached["at"]) < _CACHE_TTL_SECONDS \
                and abs((cached["change_pct"] or 0.0) - change_pct) < _CACHE_DRIFT_PCT:
            return {**cached["result"], **_quote_fields(quote), "cached": True}

        news, spy = await asyncio.gather(_fetch_news(sym), _fetch_quote("SPY"))

        explanation = await _generate_explanation(quote, news, spy)
        sources = [
            {
                "title": n.get("title"),
                "site": n.get("site"),
                "url": n.get("url"),
                "publishedDate": n.get("publishedDate"),
            }
            for n in news[:3]
            if n.get("title")
        ]
        result = {
            **_quote_fields(quote),
            "explanation": explanation,
            "sources": sources,
            "as_of": quote.get("timestamp"),
            "cached": False,
        }
        _cache[sym] = {
            "at": time.monotonic(),
            "change_pct": change_pct,
            "result": result,
        }
        # Bound the cache; symbols churn slowly so a coarse sweep is fine.
        if len(_cache) > 500:
            oldest = sorted(_cache.items(), key=lambda kv: kv[1]["at"])[:100]
            for k, _ in oldest:
                _cache.pop(k, None)
        return result


async def _generate_explanation(
    quote: dict, news: List[dict], spy: Optional[dict]
) -> str:
    from modules.agent.llm_handler import LLMHandler

    sym = quote.get("symbol")
    name = quote.get("name") or sym
    pct = quote.get("changesPercentage") or 0.0
    direction = "up" if pct >= 0 else "down"

    lines = [f"{name} ({sym}) is {direction} {abs(pct):.2f}% today at ${quote.get('price')}."]
    if spy and spy.get("changesPercentage") is not None:
        lines.append(f"Market context: the S&P 500 (SPY) is at {spy['changesPercentage']:+.2f}% today.")
    if quote.get("volume") and quote.get("avgVolume"):
        try:
            ratio = float(quote["volume"]) / float(quote["avgVolume"])
            lines.append(f"Volume is {ratio:.1f}x the average.")
        except (ValueError, ZeroDivisionError, TypeError):
            pass

    if news:
        lines.append("\nRecent headlines:")
        for n in news[:8]:
            title = n.get("title")
            if not title:
                continue
            published = (n.get("publishedDate") or "")[:16]
            snippet = (n.get("text") or "")[:160]
            lines.append(f"- [{published}] {title} — {snippet}")
    else:
        lines.append("\nNo recent ticker-specific headlines were found.")

    lines.append("\nWhy is it moving today?")

    handler = LLMHandler(user_id=None, chat_id=None, agent_type="move_explainer")
    try:
        response = await handler.acompletion(
            model=EXPLAINER_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": "\n".join(lines)},
            ],
            stream=False,
            max_tokens=1000,
            # GLM-5.1 reasons by default (Z.ai enables it server-side), which
            # takes ~40s — far too slow for a tap-to-explain UI. Disabling
            # thinking brings this to a few seconds with no quality loss on a
            # 2-sentence summarization task.
            extra_body={"thinking": {"type": "disabled"}},
        )
        text = (response.choices[0].message.content or "").strip()
        if text:
            return text
    except Exception:
        logger.exception("Move explanation LLM call failed for %s", sym)

    # Graceful fallback so the UI never shows an error state for this.
    if news:
        return f"Likely related to recent news: {news[0].get('title', '')}"
    return "No clear catalyst in today's headlines — this looks like normal market movement."
