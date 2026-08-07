"""
Starter scanners — three worked examples, not the fixed menu.

Read these to learn the pattern, then write your own with registry.save(). They
are deliberately short: a scanner is a filter over a feed plus screen.screen().

Seeded here rather than in the registry so they always work even on a fresh
sandbox, and so you can diff your own against a known-good reference.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

from . import feeds, screen


def earnings_surprises(days_back: int = 1, min_abs_surprise: float = 5.0,
                       limit: int = 40) -> List[Dict[str, Any]]:
    """Companies that just reported meaningfully away from consensus.

    Post-earnings-announcement drift is the best-documented short-horizon edge,
    which is why this is the one to start from.
    """
    out = []
    for r in feeds.earnings_calendar(days_back=days_back):
        s = screen.surprise_pct(r.get("eps"), r.get("epsEstimated"))
        if s is None or abs(s) < min_abs_surprise:
            continue
        out.append(screen.candidate(
            r["symbol"], "earnings_beat" if s > 0 else "earnings_miss",
            f"{r['symbol']} reported EPS {r['eps']} vs {r['epsEstimated']} est ({s:+.0f}%), {r.get('time','n/a')}",
            r.get("date", ""),
            {"eps": r.get("eps"), "eps_estimated": r.get("epsEstimated"),
             "surprise_pct": s, "revenue": r.get("revenue"),
             "revenue_estimated": r.get("revenueEstimated"), "time": r.get("time")},
        ))
    out.sort(key=lambda c: -abs(c["detail"]["surprise_pct"]))
    return screen.screen(out[:limit])


_RAISED = re.compile(r"price target raised|upgraded to|initiated with a buy", re.I)
_CUT = re.compile(r"price target (lowered|cut)|downgraded to", re.I)


def analyst_actions(limit: int = 60, upgrades_only: bool = True) -> List[Dict[str, Any]]:
    """Fresh upgrades and price-target raises. The action is prose in the
    headline, so it gets regexed out — there's no clean enum in this feed."""
    out = []
    for r in feeds.analyst_grade_news(300):
        title, sym = r.get("newsTitle") or "", r.get("symbol")
        if not sym or not title:
            continue
        up, down = _RAISED.search(title), _CUT.search(title)
        if (upgrades_only and not up) or (not up and not down):
            continue
        out.append(screen.candidate(
            sym, "analyst_upgrade" if up else "analyst_downgrade", title,
            (r.get("publishedDate") or "")[:10],
            {"new_grade": r.get("newGrade"), "previous_grade": r.get("previousGrade")},
            r.get("newsURL"),
        ))
    return screen.screen(out[:limit])


_PR_PATTERNS = [
    ("m_and_a", re.compile(r"\b(acquire|acquisition|merger|takeover|definitive agreement to)\b", re.I)),
    ("fda", re.compile(r"\b(fda|phase (1|2|3|i|ii|iii)|clinical trial|approval|breakthrough therapy|pdufa)\b", re.I)),
    ("contract_win", re.compile(r"\b(awarded|contract|selected by|wins?|partnership with|agreement with)\b", re.I)),
    ("guidance_raise", re.compile(r"\b(raises? (its )?(full[- ]year |fy)?guidance|increases? outlook|raises? outlook)\b", re.I)),
    ("guidance_cut", re.compile(r"\b(lowers? (its )?guidance|cuts? outlook|reduces? guidance|withdraws? guidance)\b", re.I)),
    ("product_launch", re.compile(r"\b(launches?|unveils?|introduces?|announces? availability)\b", re.I)),
]


def press_release_catalysts(limit: int = 60) -> List[Dict[str, Any]]:
    """Press releases that look like real catalysts. The litigation filter is
    doing most of the work — law-firm notices dominate this feed."""
    out = []
    for r in feeds.press_releases(400):
        title, sym = r.get("title") or "", r.get("symbol")
        if not sym or not title or screen.is_litigation_spam(title):
            continue
        for kind, pattern in _PR_PATTERNS:
            if pattern.search(title):
                out.append(screen.candidate(
                    sym, kind, title, (r.get("publishedDate") or "")[:10],
                    {"publisher": r.get("publisher")}, r.get("url")))
                break
    return screen.screen(out[:limit])


def scan_all(days_back: int = 1) -> List[Dict[str, Any]]:
    """All three starters, deduped, highest-signal first.

    Earnings lead because drift is the strongest documented edge; a name that
    also shows up in another feed carries `also_seen_in`, which is worth a look.
    This is a CANDIDATE LIST, not ideas — triage before proposing anything.
    """
    return screen.dedupe(
        earnings_surprises(days_back=days_back)
        + press_release_catalysts()
        + analyst_actions()
    )
