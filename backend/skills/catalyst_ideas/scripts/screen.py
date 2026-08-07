"""
Shared hygiene for every scanner — the traps, solved once.

These guards exist because the raw feeds are actively misleading, not merely
noisy. Each was found by running the real data. Reuse them instead of
rediscovering them:

  surprise_pct()      A $56.15 actual against a $-0.016 estimate is "+351,476%".
                      Percentages computed off near-zero estimates are garbage
                      and will dominate any ranking you build. Returns None
                      rather than a number you'd have to remember to distrust.

  is_litigation_spam()"ERASCA LEAD PLAINTIFF DEADLINE AUGUST 10th" names a
                      ticker and is not a catalyst. Law-firm class-action
                      notices are a large fraction of the press-release feed.

  screen()            Earnings feeds carry preferred shares (GMRE-PA), warrants
                      (ADVWW) and foreign lines (8370.T). Rather than
                      pattern-matching ticker suffixes — which is brittle and
                      wrong for real tickers ending in W — require a live quote
                      that clears price/volume/market-cap floors. Untradeable
                      names drop out by construction.

Candidate shape (what scanners return, what triage consumes):

    {"symbol", "catalyst_type", "headline", "date", "detail", "source_url"}

catalyst_type must be one of CATALYST_TYPES so the scorecard can bucket by it.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .feeds import quotes

# Must match schemas/trade_ideas.py CATALYST_TYPES — the scorecard groups on it.
CATALYST_TYPES = [
    "earnings_beat", "earnings_miss", "guidance_raise", "guidance_cut",
    "analyst_upgrade", "analyst_downgrade", "m_and_a", "fda", "contract_win",
    "product_launch", "legal_regulatory", "insider_buying", "index_inclusion",
    "macro", "other",
]

MIN_ABS_ESTIMATE = 0.10        # below this, surprise % is meaningless
# Beyond this the "surprise" is a one-time charge, a restated figure or a
# non-comparable item — not a beat you can trade. Real drift-worthy surprises
# live in the 5-100% band; -8477% is an artifact every time.
MAX_ABS_SURPRISE = 300.0
MIN_PRICE = 3.0
MIN_AVG_VOLUME = 300_000
MIN_MARKET_CAP = 200_000_000

_LITIGATION = re.compile(
    r"lead plaintiff|class action|investor alert|securities fraud|deadline"
    r"|investigation on behalf|shareholder rights|reminds investors"
    r"|law offices|rosen law|bragar eagel|pomerantz|levi & korsinsky|kessler topaz",
    re.I,
)


def is_litigation_spam(title: str) -> bool:
    """True for law-firm notices that mention a ticker but aren't catalysts."""
    return bool(_LITIGATION.search(title or ""))


def surprise_pct(actual: Optional[float], estimate: Optional[float],
                 min_abs_estimate: float = MIN_ABS_ESTIMATE,
                 max_abs_surprise: float = MAX_ABS_SURPRISE) -> Optional[float]:
    """Percentage surprise, or None when the number wouldn't mean anything.

    None is returned in two cases, both of which produce garbage rankings if you
    compute the ratio yourself:
      - the estimate is too small (a $-0.016 consensus makes any actual "huge")
      - the result is implausibly large, which signals a one-time charge or a
        non-comparable figure rather than a tradeable beat

    Always check for None. Do not treat it as zero.
    """
    if actual is None or estimate is None:
        return None
    if abs(estimate) < min_abs_estimate:
        return None
    # Round before the bounds check: (0.40-0.10)/0.10 is 300.00000000000006 in
    # floating point, and an exactly-at-the-cap surprise should be kept.
    pct = round((actual - estimate) / abs(estimate) * 100.0, 1)
    return None if abs(pct) > max_abs_surprise else pct


def candidate(symbol: str, catalyst_type: str, headline: str, when: str = "",
              detail: Optional[Dict[str, Any]] = None,
              source_url: Optional[str] = None) -> Dict[str, Any]:
    """Build a candidate in the shape triage expects."""
    if catalyst_type not in CATALYST_TYPES:
        raise ValueError(f"catalyst_type must be one of {CATALYST_TYPES}")
    return {"symbol": symbol.upper(), "catalyst_type": catalyst_type,
            "headline": (headline or "").strip(), "date": when,
            "detail": detail or {}, "source_url": source_url}


def screen(candidates: List[Dict[str, Any]], *, min_price: float = MIN_PRICE,
           min_avg_volume: int = MIN_AVG_VOLUME,
           min_market_cap: int = MIN_MARKET_CAP) -> List[Dict[str, Any]]:
    """Attach live quotes and drop anything untradeable.

    Adds a `quote` block with price, volume, marketCap and `rvol` (today's
    volume / average). rvol > 1.5 means the market is corroborating your
    catalyst; rvol < 1 on a "big" headline usually means nobody cares.
    """
    if not candidates:
        return []
    # A dot is an exchange suffix (8370.T, 1808.TW). These have real quotes and
    # real market caps, so the liquidity floors alone won't catch them — but the
    # user can't trade them here.
    candidates = [c for c in candidates if "." not in c["symbol"]]
    qmap = quotes([c["symbol"] for c in candidates])
    kept = []
    for c in candidates:
        q = qmap.get(c["symbol"])
        if not q:
            continue
        price, avg_vol, cap = q.get("price") or 0, q.get("avgVolume") or 0, q.get("marketCap") or 0
        if price < min_price or avg_vol < min_avg_volume or cap < min_market_cap:
            continue
        vol = q.get("volume") or 0
        c["quote"] = {
            "price": price, "changesPercentage": q.get("changesPercentage"),
            "volume": vol, "avgVolume": avg_vol, "marketCap": cap,
            # None, not 0, when today's volume isn't populated — the feed
            # reports volume=0 for perfectly liquid names outside RTH (AAPL
            # does it post-close), and a 0.0 here would read as "nobody cares".
            "rvol": round(vol / avg_vol, 2) if (avg_vol and vol) else None,
        }
        kept.append(c)
    return kept


def dedupe(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """One candidate per symbol — the first wins, so pass your highest-signal
    scanner's output first. A name showing up in several feeds at once is worth
    noting; `also_seen_in` records the extra catalyst types."""
    seen: Dict[str, Dict[str, Any]] = {}
    for c in candidates:
        s = c["symbol"]
        if s in seen:
            seen[s].setdefault("also_seen_in", []).append(c["catalyst_type"])
        else:
            seen[s] = c
    return list(seen.values())
