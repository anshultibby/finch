"""
Verified market-wide data feeds — the raw material for scanners.

Everything here was probed against the live API and works. The point of this
module is that you (the agent) do NOT have to discover the data surface by trial
and error, and do not have to guess which endpoints are real. Build scanners on
these.

Each feed returns raw rows from the source, lightly normalized. Filtering,
ranking and interpretation belong in your scanner, not here.

WHAT DOESN'T WORK (verified — don't waste turns retrying):
  /upgrades-downgrades          -> returns [] on this plan
  /stable/upgrades-downgrades   -> 404
  /stable/earnings-surprises    -> 404
Use analyst_grade_news() for analyst actions instead.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List

from skills.financial_modeling_prep.scripts.api import fmp, fmp_stable


def earnings_calendar(days_back: int = 1, days_forward: int = 0) -> List[Dict[str, Any]]:
    """Every company reporting in the window, market-wide.

    Rows: {symbol, date, time ('bmo'|'amc'), eps, epsEstimated, revenue,
           revenueEstimated, fiscalDateEnding}

    `eps` is populated once a company has reported; `epsEstimated` is consensus.
    Both are null for many foreign listings. ~5,000 rows over 2 days, so filter
    hard. See screen.surprise_pct() before computing surprises yourself — the
    naive formula blows up on near-zero estimates.
    """
    frm = (date.today() - timedelta(days=max(days_back, 0))).isoformat()
    to = (date.today() + timedelta(days=max(days_forward, 0))).isoformat()
    r = fmp("/earning_calendar", {"from": frm, "to": to})
    return r if isinstance(r, list) else []


def analyst_grade_news(limit: int = 300) -> List[Dict[str, Any]]:
    """Latest analyst actions across the market.

    Rows: {symbol, publishedDate, newsTitle, newsURL, publisher, newGrade,
           previousGrade}

    The action lives in `newsTitle` as prose — "price target raised to $300 from
    $295 at Wedbush", "upgraded to Buy". Parse it; there is no clean enum.
    """
    r = fmp_stable("/grades-latest-news", {"limit": limit})
    return r if isinstance(r, list) else []


def analyst_grades_for(symbol: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Per-symbol analyst grade history, WITH a clean `action` field
    ('upgrade' | 'downgrade' | 'maintain') — unlike the market-wide feed.

    Use this to confirm a single name once a scanner has surfaced it.
    """
    r = fmp_stable("/grades", {"symbol": symbol, "limit": limit})
    return r if isinstance(r, list) else []


def press_releases(limit: int = 300) -> List[Dict[str, Any]]:
    """Company press releases across the market.

    Rows: {symbol, publishedDate, publisher, title, text, url}

    Mostly noise. A large fraction is law-firm class-action spam that names a
    ticker but is not a catalyst — screen.is_litigation_spam() drops it.
    """
    r = fmp_stable("/news/press-releases-latest", {"limit": limit})
    return r if isinstance(r, list) else []


def press_releases_for(symbol: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Press releases for one company — for confirming a candidate's story."""
    r = fmp(f"/press-releases/{symbol}", {"limit": limit})
    return r if isinstance(r, list) else []


def stock_news(symbols: List[str] | str, limit: int = 50) -> List[Dict[str, Any]]:
    """News for specific tickers. Rows: {symbol, publishedDate, title, text,
    site, url}. Use for catalyst triage — reading the actual story."""
    tickers = symbols if isinstance(symbols, str) else ",".join(symbols)
    r = fmp("/stock_news", {"tickers": tickers, "limit": limit})
    return r if isinstance(r, list) else []


def movers() -> Dict[str, List[Dict[str, Any]]]:
    """Today's gainers / losers / most-active.

    Price movement WITHOUT a reason is not a catalyst — use this to corroborate
    a catalyst you already found, or to hunt for an unexplained move worth
    investigating. Never propose an idea off this alone.
    """
    def _l(path):
        r = fmp(path)
        return r if isinstance(r, list) else []
    return {"gainers": _l("/stock_market/gainers"),
            "losers": _l("/stock_market/losers"),
            "actives": _l("/stock_market/actives")}


def quotes(symbols: List[str]) -> Dict[str, Dict[str, Any]]:
    """Batch quotes keyed by symbol, chunked for you.

    Fields include price, changesPercentage, volume, avgVolume, marketCap,
    yearHigh/yearLow, pe. A symbol with no quote (delisted, preferred class,
    foreign line) is simply absent — which is itself a useful filter.
    """
    out: Dict[str, Dict[str, Any]] = {}
    uniq = sorted({s.upper() for s in symbols})
    for i in range(0, len(uniq), 100):
        try:
            r = fmp("/quote/" + ",".join(uniq[i:i + 100]))
            # A single-symbol request comes back as a bare dict, not a list.
            # Treating that as "no results" silently empties any scanner that
            # narrows to one name, so normalize before iterating.
            if isinstance(r, dict):
                r = [r] if r.get("symbol") else []
            for q in (r if isinstance(r, list) else []):
                if isinstance(q, dict) and q.get("symbol"):
                    out[q["symbol"]] = q
        except Exception:
            continue
    return out
