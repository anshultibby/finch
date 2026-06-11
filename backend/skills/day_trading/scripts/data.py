"""
Market data for day trading — candidate scanning + session-correct bars.

Built on the polygon_io skill. Two-stage scan keeps API usage sane:

  1. scan_market()      — ONE full-market snapshot call → coarse "in play" list
                          (price, gap %, early volume vs prior day).
  2. refine_candidates() — 2 calls per surviving symbol → TRUE first-5-min RVOL
                          (vs 14-day baseline, the Zarattini filter) + ATR(14)
                          + today's RTH bars, ready for orb_signal().

Plus rth_today_bars(), a session-correct replacement for get_today_bars()
(which trusts the server clock and includes premarket — both wrong here).
"""
from datetime import timedelta
from typing import Dict, Any, List, Optional

from skills.polygon_io.scripts.api import polygon
from skills.polygon_io.scripts.market.intraday import get_intraday_bars
from .clock import now_et, rth_only, group_rth_by_day
from .indicators import atr


def rth_today_bars(symbol: str, timespan: str = "1min") -> List[Dict]:
    """Today's regular-trading-hours bars (ET-correct, premarket stripped)."""
    d = now_et().date()
    resp = get_intraday_bars(symbol, d.isoformat(), d.isoformat(), timespan)
    if "error" in resp:
        return []
    return rth_only(resp["bars"], d)


def scan_market(min_price: float = 5.0, max_price: float = 2000.0,
                min_day_volume: float = 500_000, min_abs_gap_pct: float = 1.0,
                top_n: int = 40) -> List[Dict[str, Any]]:
    """
    Stage 1: one snapshot call across the whole US market → coarse in-play list.

    Uses today's volume vs the SAME stock's full prior day (a rough RVOL proxy —
    good enough to cut 10,000 tickers to ~40) plus the overnight gap. Run it a
    few minutes after the open. Returns dicts sorted by the proxy, descending:

        {"symbol", "price", "gap_pct", "day_volume", "prev_volume", "rvol_proxy"}
    """
    resp = polygon("/v2/snapshot/locale/us/markets/stocks/tickers")
    out = []
    for t in (resp or {}).get("tickers", []):
        day, prev = t.get("day") or {}, t.get("prevDay") or {}
        price = day.get("c") or (t.get("min") or {}).get("c") or 0
        vol, pvol = day.get("v") or 0, prev.get("v") or 0
        pclose = prev.get("c") or 0
        if not (min_price < price < max_price) or vol < min_day_volume or not pclose:
            continue
        gap_pct = 100 * (day.get("o", pclose) - pclose) / pclose
        if abs(t.get("todaysChangePerc") or 0) < min_abs_gap_pct and abs(gap_pct) < min_abs_gap_pct:
            continue
        out.append({
            "symbol": t["ticker"], "price": round(price, 2),
            "gap_pct": round(gap_pct, 2),
            "change_pct": round(t.get("todaysChangePerc") or 0, 2),
            "day_volume": vol, "prev_volume": pvol,
            "rvol_proxy": round(vol / pvol, 2) if pvol else 0,
        })
    out.sort(key=lambda x: x["rvol_proxy"], reverse=True)
    return out[:top_n]


def refine_candidates(symbols: List[str], min_rvol: float = 1.5,
                      min_atr: float = 0.50, baseline_days: int = 14,
                      top_n: int = 10) -> List[Dict[str, Any]]:
    """
    Stage 2: per surviving symbol (keep the input list ≤ ~25 — 2 API calls each):
    true first-5-minute RVOL vs the prior `baseline_days`, daily ATR(14), and
    today's RTH 1-min bars. Returns, sorted by RVOL desc, top_n of:

        {"symbol", "rvol", "atr14", "price", "bars": [...today's RTH 1-min...]}

    These are the "stocks in play". Feed `bars` + `atr14` straight into
    orb_signal(); pass the list to the LLM for catalyst triage (see SKILL.md).
    """
    today = now_et().date()
    start = (today - timedelta(days=baseline_days * 2)).isoformat()  # calendar pad for weekends
    refined = []
    for sym in symbols:
        intra = get_intraday_bars(sym, start, today.isoformat(), "1min")
        daily = polygon(f"/v2/aggs/ticker/{sym.upper()}/range/1/day/{start}/{today.isoformat()}",
                        {"adjusted": "true", "sort": "asc", "limit": 120})
        if "error" in intra or not (daily or {}).get("results"):
            continue
        by_day = group_rth_by_day(intra["bars"])
        days = sorted(by_day.keys())
        if today.isoformat() not in days:
            continue
        prior = days[:-1][-baseline_days:]

        def first5_vol(day_bars):
            first_ts = int(day_bars[0]["timestamp"])
            return sum(float(b["volume"]) for b in day_bars
                       if int(b["timestamp"]) < first_ts + 5 * 60 * 1000)

        base = [first5_vol(by_day[d]) for d in prior if by_day[d]]
        today_bars = by_day[today.isoformat()]
        if not base or not today_bars:
            continue
        rvol = first5_vol(today_bars) / (sum(base) / len(base)) if sum(base) else 0

        dbars = [{"high": r["h"], "low": r["l"], "close": r["c"], "timestamp": r["t"]}
                 for r in daily["results"][:-1]]  # exclude today's partial bar
        a = atr(dbars, 14)
        price = float(today_bars[-1]["close"])
        if rvol >= min_rvol and a and a >= min_atr:
            refined.append({"symbol": sym.upper(), "rvol": round(rvol, 2),
                            "atr14": round(a, 3), "price": round(price, 2),
                            "bars": today_bars})
    refined.sort(key=lambda x: x["rvol"], reverse=True)
    return refined[:top_n]


def stocks_in_play(top_n: int = 10, scan_top_n: int = 25,
                   min_rvol: float = 1.5) -> List[Dict[str, Any]]:
    """Stage 1 + stage 2 in one call. ~1 + 2×scan_top_n API calls."""
    coarse = scan_market(top_n=scan_top_n)
    return refine_candidates([c["symbol"] for c in coarse],
                             min_rvol=min_rvol, top_n=top_n)
