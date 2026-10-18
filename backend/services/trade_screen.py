"""Cheap pre-flight screen for day-trading entry sessions.

The nightly planner and the intraday open-scan jobs used to spin up a full
coordinator session every time they fired — even on quiet days with no tradeable
setup. That is the bulk of the day-trading credit spend.

This module asks the OpenAI **Decisions API** (`POST /v1/decisions`, model
`gpt-6-luna` — $0.10/Mtok in, no output charge, ~150 ms) a single screening
question over a cheap market snapshot: *is the backdrop active enough that a full
intraday entry-scan session is worth running right now?* If the answer is a low
probability, the caller skips the expensive Haiku session.

Design guarantees:
  - **Fail-open.** No key, screen disabled, network/parse error, or any exception
    → `run=True`. The screen can only ever *skip* a session, never place, size,
    or alter a trade, and it must never block trading on its own failure.
  - **Entry scans only.** The nightly review is load-bearing (it schedules the
    next session's wakeups and stands down open risk) and is never screened out —
    callers pass it through unconditionally. See `job_scheduler.run_job`.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import httpx

from core.config import Config
from utils.logger import get_logger

logger = get_logger(__name__)

_DECISIONS_URL = "https://api.openai.com/v1/decisions"
_DECISIONS_MODEL = "gpt-6-luna"
# Index + volatility proxies — a cheap, always-available FMP snapshot that needs
# no brokerage connection. VIXY tracks VIX exposure (^VIX isn't on FMP /quote).
_BACKDROP_SYMBOLS = ["SPY", "QQQ", "VIXY"]


@dataclass
class ScreenResult:
    run: bool
    probability: Optional[float]
    reason: str


def _fmt_snapshot(quotes: dict) -> str:
    lines: List[str] = []
    for sym in _BACKDROP_SYMBOLS:
        q = quotes.get(sym)
        if not q:
            continue
        price = q.get("price")
        change_pct = q.get("changesPercentage")
        if price is None:
            continue
        chg = f"{change_pct:+.2f}%" if isinstance(change_pct, (int, float)) else "n/a"
        lines.append(f"{sym}: {price} ({chg} today)")
    return "\n".join(lines)


async def should_run_entry_scan() -> ScreenResult:
    """Decide whether an intraday open-scan session is worth running now."""
    if not Config.TRADE_SCREEN_ENABLED:
        return ScreenResult(True, None, "screen disabled")
    if not Config.OPENAI_API_KEY:
        return ScreenResult(True, None, "no OpenAI key — fail-open")

    try:
        from services.monitoring.inputs import batch_quotes
        quotes = await batch_quotes(_BACKDROP_SYMBOLS)
        snapshot = _fmt_snapshot(quotes)
        if not snapshot:
            return ScreenResult(True, None, "no market snapshot — fail-open")

        payload = {
            "model": _DECISIONS_MODEL,
            "input": (
                "US market backdrop for an intraday long-only day-trading open "
                "scan (opening-range breakout style). Quotes:\n" + snapshot
            ),
            "questions": [{
                "type": "predicate",
                "name": "warrants_session",
                "instructions": (
                    "Is the market backdrop active enough right now — meaningful "
                    "index movement and/or elevated volatility — that scanning "
                    "for an intraday long entry is worthwhile? Answer with the "
                    "probability that a full scan is worth running. A flat, "
                    "quiet tape with low volatility should score low."
                ),
            }],
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                _DECISIONS_URL,
                headers={"Authorization": f"Bearer {Config.OPENAI_API_KEY}"},
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        answers = data.get("answers") or []
        prob = next(
            (a.get("probability") for a in answers
             if a.get("name") == "warrants_session"),
            None,
        )
        if not isinstance(prob, (int, float)):
            return ScreenResult(True, None, "no probability in response — fail-open")

        threshold = Config.TRADE_SCREEN_MIN_PROBABILITY
        run = prob >= threshold
        reason = f"screen p={prob:.2f} (threshold {threshold:.2f})"
        logger.info(f"Entry-scan screen: {'RUN' if run else 'SKIP'} — {reason}")
        return ScreenResult(run, float(prob), reason)
    except Exception as e:
        logger.warning(f"Entry-scan screen failed, running session (fail-open): {e}")
        return ScreenResult(True, None, f"screen error — fail-open: {e}")
