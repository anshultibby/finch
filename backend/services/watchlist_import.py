"""
Import a watchlist from screenshots.

A user pastes/uploads screenshots of any brokerage or watchlist app (Robinhood,
Fidelity, a TradingView column, a tweet, …) and we extract the tickers with a
vision model, then validate each against FMP so junk/hallucinations never reach
the DB. Company names that the screenshot showed without a ticker are resolved
to a symbol via FMP search.

Used by routes/watchlist.py — the route owns the DB writes; this module is the
pure extract+resolve step.
"""
from __future__ import annotations

import asyncio
import json
import re
from typing import Any

from core.constants import Models
from modules.agent.llm_handler import LLMHandler
from utils.logger import get_logger

logger = get_logger(__name__)

# Haiku is fast, cheap, and vision-capable — plenty for reading tickers off an image.
_VISION_MODEL = Models.CLAUDE_HAIKU_4_5
_MAX_IMAGES = 8
_MAX_CANDIDATES = 60

_SYSTEM_PROMPT = (
    "You read screenshots of stock brokerage, watchlist, portfolio, or finance "
    "apps and extract the publicly-traded securities shown. For each row/tile, "
    "return the ticker symbol if visible, and the company/instrument name if "
    "visible. Include ETFs and ADRs. Ignore crypto, currencies, options, index "
    "values, P&L numbers, and UI chrome. "
    "Respond with ONLY a JSON array, no prose, of the form "
    '[{"symbol": "AAPL", "name": "Apple"}, ...]. '
    "If a row shows a name but no ticker, set symbol to null and fill name. "
    "If no securities are visible, return []."
)


def _as_data_url(image: str) -> str:
    """Accept either a full data URL or raw base64 and return a data URL."""
    if image.startswith("data:"):
        return image
    return f"data:image/png;base64,{image}"


def _parse_json_array(text: str) -> list[dict]:
    """Pull the first JSON array out of the model's reply, tolerating fences/prose."""
    if not text:
        return []
    # Strip ```json fences if present.
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end == -1 or end < start:
        return []
    try:
        data = json.loads(text[start:end + 1])
    except (ValueError, TypeError):
        return []
    return [d for d in data if isinstance(d, dict)]


async def extract_candidates(images: list[str]) -> list[dict]:
    """Run the vision model over the screenshots and return raw {symbol, name} dicts."""
    content: list[dict] = [{
        "type": "text",
        "text": "Extract the tickers/securities from these screenshots.",
    }]
    for img in images[:_MAX_IMAGES]:
        content.append({"type": "image_url", "image_url": {"url": _as_data_url(img)}})

    handler = LLMHandler(user_id=None, chat_id=None, agent_type="watchlist_import")
    response = await handler.acompletion(
        model=_VISION_MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ],
        stream=False,
        max_tokens=1500,
    )
    text = (response.choices[0].message.content or "").strip()
    return _parse_json_array(text)[:_MAX_CANDIDATES]


def _pick_match(results: list[dict], wanted_symbol: str | None) -> dict | None:
    """Choose the best FMP search hit: exact symbol > major US exchange > first."""
    if not results:
        return None
    if wanted_symbol:
        ws = wanted_symbol.upper()
        for r in results:
            if (r.get("symbol") or "").upper() == ws:
                return r
    for r in results:
        if (r.get("exchangeShortName") or "").upper() in ("NASDAQ", "NYSE", "AMEX"):
            return r
    return results[0]


def _resolve_one(cand: dict) -> dict | None:
    """Validate a single candidate against FMP; return {symbol, name} or None."""
    from skills.financial_modeling_prep.scripts.search.search import search

    symbol = (cand.get("symbol") or "").strip()
    name = (cand.get("name") or "").strip()
    query = symbol or name
    if not query:
        return None
    try:
        results = search(query, limit=5)
    except Exception:
        results = []
    if not results and symbol and name:
        try:
            results = search(name, limit=5)
        except Exception:
            results = []
    match = _pick_match(results if isinstance(results, list) else [], symbol or None)
    if not match or not match.get("symbol"):
        return None
    return {"symbol": match["symbol"].upper(), "name": match.get("name") or name or None}


async def resolve_candidates(candidates: list[dict]) -> tuple[list[dict], list[str]]:
    """Resolve candidates to real tickers concurrently. Returns (resolved, unresolved)."""
    if not candidates:
        return [], []
    resolved_raw = await asyncio.gather(
        *(asyncio.to_thread(_resolve_one, c) for c in candidates)
    )
    resolved: list[dict] = []
    unresolved: list[str] = []
    seen: set[str] = set()
    for cand, match in zip(candidates, resolved_raw):
        if match and match["symbol"] not in seen:
            seen.add(match["symbol"])
            resolved.append(match)
        elif not match:
            label = (cand.get("symbol") or cand.get("name") or "").strip()
            if label:
                unresolved.append(label)
    return resolved, unresolved


async def extract_and_resolve(images: list[str]) -> tuple[list[dict], list[str]]:
    """Full pipeline: screenshots → validated [{symbol, name}], plus unresolved labels."""
    candidates = await extract_candidates(images)
    if not candidates:
        return [], []
    return await resolve_candidates(candidates)
