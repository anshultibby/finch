"""
Move Explainer — instant, grounded "why is this moving?" intelligence.

Given a symbol, fetches today's quote + recent headlines (FMP) plus measured
context (how unusual the move is for this stock, market/sector benchmarks,
volume, earnings timing, the macro tape — see services.monitoring.move_context)
and asks a fast model for a structured read: is this noise, news with the story
intact, or a narrative shift — and is the driver macro, sector or company? Results are cached in-memory per symbol and shared across all
users (the explanation of why NVDA is up today is the same for everyone), so
the marginal cost of the feature stays near zero.

The cache invalidates when the price has moved materially since the cached
explanation was generated — an explanation of "+2% on analyst upgrade" should
not survive the stock swinging to -4%.
"""
import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional

from services.insight_model import DEFAULT_INSIGHT_MODEL
from services.monitoring.cache import TTLCache
from services.monitoring.move_context import (
    DRIVERS, FRAMEWORK, VERDICTS, context_lines, macro_backdrop, macro_lines, move_context,
)
from services.monitoring.narrate import narrate

logger = logging.getLogger(__name__)

# Symbol-scoped and cached across all users, so this can't be resolved per
# tenant without shattering that cache — and it needs no holdings to do its
# job, only a public quote and headlines. Flat US-hosted default instead.
EXPLAINER_MODEL = DEFAULT_INSIGHT_MODEL

# Cache entries live 20 min, and are also dropped if the live change% has
# drifted more than _CACHE_DRIFT_PCT points from when the entry was generated.
# Bounded so a wide symbol churn can't grow it without limit.
_CACHE_DRIFT_PCT = 1.0
_explain_cache = TTLCache(ttl_seconds=20 * 60, max_entries=500)

_SYSTEM_PROMPT = f"""You are a sharp, honest markets analyst explaining a stock's move today to a regular investor checking their phone. You are given measured context (how unusual the move is for this stock, market and sector benchmarks, volume, earnings timing, the macro tape) and recent headlines.

{FRAMEWORK}

Respond with ONLY a JSON object, no prose around it:
{{"verdict": "noise" | "news" | "narrative_shift",
  "driver": "macro" | "sector" | "company",
  "headline": "<= 70 chars, the why in plain words — no ticker, no percentage",
  "explanation": "2-3 short sentences: what happened, how much is market/sector vs the company, and whether the story changed",
  "watch": "one short line: what would confirm or change this read"}}

Plain English, no jargon or hedging boilerplate, never "as an AI". Don't repeat the price or percentage — the user already sees them."""


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
    """Return {symbol, name, price, change_pct, verdict, driver, headline,
    explanation, watch, context, sources, as_of}.

    `verdict` is noise | news | narrative_shift and `driver` is macro | sector |
    company (see services.monitoring.move_context.FRAMEWORK); `context` holds
    the measured inputs (typical move, benchmarks, volume, earnings timing).

    Raises ValueError if no quote exists for the symbol.
    """
    sym = symbol.upper().strip()

    quote = await _fetch_quote(sym)
    if not quote:
        raise ValueError(f"No quote found for {sym}")
    change_pct = quote.get("changesPercentage") or 0.0

    def _stable(meta) -> bool:
        return abs(((meta or {}).get("change_pct") or 0.0) - change_pct) < _CACHE_DRIFT_PCT

    cached = _explain_cache.get(sym, validate=_stable)
    if cached is not None:
        return {**cached, **_quote_fields(quote), "cached": True}

    async with _explain_cache.lock(sym):
        # Re-check under the lock — another request may have just generated it.
        cached = _explain_cache.get(sym, validate=_stable)
        if cached is not None:
            return {**cached, **_quote_fields(quote), "cached": True}

        news = await _fetch_news(sym)

        read = await _generate_explanation(quote, news)
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
            **read,
            "sources": sources,
            "as_of": quote.get("timestamp"),
            "cached": False,
        }
        _explain_cache.set(sym, result, meta={"change_pct": change_pct})
        return result


def _parse(text: str) -> Optional[Dict[str, str]]:
    """Pull the JSON object out of the model's reply; None if it isn't usable."""
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict) or not data.get("explanation"):
        return None
    if data.get("verdict") not in VERDICTS:
        data["verdict"] = "noise"
    if data.get("driver") not in DRIVERS:
        data["driver"] = "company"
    return {k: str(data.get(k) or "").strip() for k in ("verdict", "driver", "headline", "explanation", "watch")}


async def _generate_explanation(quote: dict, news: List[dict]) -> Dict[str, Any]:
    """Structured read of today's move: verdict, driver, headline, explanation, watch,
    plus the measured context it was based on."""
    sym = quote.get("symbol")
    name = quote.get("name") or sym
    pct = quote.get("changesPercentage") or 0.0
    direction = "up" if pct >= 0 else "down"

    backdrop = await macro_backdrop()
    ctx = await move_context(sym, quote, backdrop)

    lines = [f"{name} ({sym}) is {direction} {abs(pct):.2f}% today at ${quote.get('price')}."]
    lines += context_lines(ctx)
    lines.append("")
    lines += macro_lines(backdrop)

    if news:
        lines.append(f"\nRecent {sym} headlines (newest first):")
        for n in news[:8]:
            title = n.get("title")
            if not title:
                continue
            published = (n.get("publishedDate") or "")[:16]
            snippet = (n.get("text") or "")[:200]
            lines.append(f"- [{published}] {title} — {snippet}")
    else:
        lines.append(f"\nNo recent {sym}-specific headlines were found.")

    lines.append("\nJudge today's move and return the JSON.")

    # Thinking stays off for this short grounded task (see narrate); on GLM it
    # otherwise takes ~40s — far too slow for a tap-to-explain UI. Flat,
    # symbol-scoped model since the cache is shared across all users.
    read = await narrate(
        system_prompt=_SYSTEM_PROMPT,
        user_content="\n".join(lines),
        agent_type="move_explainer",
        max_tokens=1000,
        model=EXPLAINER_MODEL,
        parser=_parse,
    )
    if not read:
        # Graceful fallback so the UI never shows an error state for this:
        # lean on the measured prior rather than guess at a cause.
        routine = ctx["prior"] != "stock-specific"
        if news and not routine:
            explanation = f"Likely related to recent news: {news[0].get('title', '')}"
        elif ctx["prior"] == "mostly explained by the market/sector":
            explanation = "This mostly tracks the market and its sector today — no company-specific catalyst in the headlines."
        else:
            explanation = "No clear catalyst in today's headlines — this looks like normal movement for this stock."
        read = {
            "verdict": "noise" if routine else "news",
            "driver": "macro" if routine else "company",
            "headline": "",
            "explanation": explanation,
            "watch": "",
        }
    return {**read, "context": ctx}
