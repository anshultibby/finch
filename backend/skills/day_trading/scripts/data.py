"""
Market data for day trading — candidate scanning + session-correct bars.

Split across two providers because the Polygon tier blocks SAME-DAY data
(today's bars and the market snapshot both return "not authorized"; multi-day
ranges silently truncate at yesterday) while FMP serves it fine:

  - Polygon: history — prior-day 1-min bars (RVOL baseline) + daily bars (ATR).
  - FMP: everything same-day — today's intraday bars, and the movers/quote
    fallback when the Polygon snapshot is denied.

Two-stage scan keeps API usage sane:

  1. scan_market()      — ONE full-market snapshot call (FMP movers + batch
                          quotes when denied) → coarse "in play" list
                          (price, gap %, volume vs typical).
  2. refine_candidates() — per surviving symbol: TRUE first-5-min RVOL
                          (vs 14-day baseline, the Zarattini filter) + ATR(14)
                          + today's RTH bars, ready for orb_signal().

Plus rth_today_bars(), a session-correct replacement for get_today_bars()
(which trusts the server clock and includes premarket — both wrong here).
"""
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from skills.financial_modeling_prep.scripts.api import fmp
from skills.polygon_io.scripts.api import polygon
from skills.polygon_io.scripts.market.intraday import get_intraday_bars
from .clock import _ET, _et_offset, now_et, to_et, rth_only, group_rth_by_day
from .indicators import atr


def _fmp_bars_to_polygon(rows: List[Dict]) -> List[Dict]:
    """FMP historical-chart rows (naive ET 'date', newest first) → polygon bar
    shape (unix-ms 'timestamp', ascending) so clock/setups helpers just work."""
    out = []
    for r in rows or []:
        try:
            naive = datetime.strptime(r["date"], "%Y-%m-%d %H:%M:%S")
        except (KeyError, ValueError):
            continue
        if _ET is not None:
            et = naive.replace(tzinfo=_ET)
        else:  # manual-DST fallback: offset by the date itself (close enough)
            from datetime import timezone
            et = naive.replace(tzinfo=timezone(_et_offset(
                naive.replace(tzinfo=timezone.utc))))
        out.append({
            "timestamp": int(et.timestamp() * 1000), "date": r["date"],
            "open": r.get("open"), "high": r.get("high"),
            "low": r.get("low"), "close": r.get("close"),
            "volume": float(r.get("volume") or 0),
        })
    out.sort(key=lambda b: b["timestamp"])
    return out


def fmp_intraday_bars(symbol: str, day: str, timespan: str = "1min") -> List[Dict]:
    """One ET day of intraday bars from FMP (works for TODAY on our plan),
    polygon-shaped. Intervals: 1min/5min/15min/30min/1hour."""
    rows = fmp(f"/historical-chart/{timespan}/{symbol.upper()}",
               {"from": day, "to": day})
    return _fmp_bars_to_polygon(rows if isinstance(rows, list) else [])


def rth_today_bars(symbol: str, timespan: str = "1min") -> List[Dict]:
    """Today's regular-trading-hours bars (ET-correct, premarket stripped).
    Polygon first; falls back to FMP when the tier denies same-day data."""
    d = now_et().date()
    resp = get_intraday_bars(symbol, d.isoformat(), d.isoformat(), timespan)
    bars = [] if "error" in resp else resp["bars"]
    if not bars:
        bars = fmp_intraday_bars(symbol, d.isoformat(), timespan)
    return rth_only(bars, d)


def scan_market(min_price: float = 5.0, max_price: float = 2000.0,
                min_day_volume: float = 500_000, min_abs_gap_pct: float = 1.0,
                top_n: int = 40) -> List[Dict[str, Any]]:
    """
    Stage 1: one snapshot call across the whole US market → coarse in-play list.

    Uses today's volume vs the SAME stock's full prior day (a rough RVOL proxy —
    good enough to cut 10,000 tickers to ~40) plus the overnight gap. Run it a
    few minutes after the open. Returns dicts sorted by the proxy, descending:

        {"symbol", "price", "gap_pct", "day_volume", "prev_volume", "rvol_proxy"}

    When the Polygon snapshot is tier-blocked, falls back to FMP movers
    (gainers + losers + actives → batch quotes); there `prev_volume` is the
    3-month average volume and the proxy is volume/avgVolume — same spirit.
    """
    resp = polygon("/v2/snapshot/locale/us/markets/stocks/tickers")
    if not (resp or {}).get("tickers"):
        return _scan_market_fmp(min_price, max_price, min_day_volume,
                                min_abs_gap_pct, top_n)
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


def _scan_market_fmp(min_price: float, max_price: float, min_day_volume: float,
                     min_abs_gap_pct: float, top_n: int) -> List[Dict[str, Any]]:
    """Coarse in-play list without the Polygon snapshot: FMP gainers + losers +
    actives (~150 names), then one batch-quote pass for volume/avgVolume and
    the overnight gap. Output shape matches scan_market()."""
    symbols: List[str] = []
    for ep in ("/stock_market/gainers", "/stock_market/losers",
               "/stock_market/actives"):
        rows = fmp(ep)
        for r in (rows if isinstance(rows, list) else []):
            s = r.get("symbol")
            if s and s not in symbols:
                symbols.append(s)
    out = []
    for i in range(0, len(symbols), 50):
        quotes = fmp("/quote/" + ",".join(symbols[i:i + 50]))
        for q in (quotes if isinstance(quotes, list) else []):
            price = q.get("price") or 0
            vol, avg_vol = q.get("volume") or 0, q.get("avgVolume") or 0
            pclose = q.get("previousClose") or 0
            if not (min_price < price < max_price) or vol < min_day_volume or not pclose:
                continue
            gap_pct = 100 * ((q.get("open") or pclose) - pclose) / pclose
            change_pct = q.get("changesPercentage") or 0
            if abs(change_pct) < min_abs_gap_pct and abs(gap_pct) < min_abs_gap_pct:
                continue
            out.append({
                "symbol": q["symbol"], "price": round(price, 2),
                "gap_pct": round(gap_pct, 2),
                "change_pct": round(change_pct, 2),
                "day_volume": vol, "prev_volume": avg_vol,
                "rvol_proxy": round(vol / avg_vol, 2) if avg_vol else 0,
            })
    out.sort(key=lambda x: x["rvol_proxy"], reverse=True)
    return out[:top_n]


def refine_candidates(symbols: List[str], min_rvol: float = 1.5,
                      min_atr: float = 0.50, baseline_days: int = 14,
                      top_n: int = 10) -> List[Dict[str, Any]]:
    """
    Stage 2: per surviving symbol (keep the input list ≤ ~25 — 2-3 API calls each):
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
        # Polygon serves the prior-day baseline even on the tier that blocks
        # same-day data (the range just truncates at yesterday) …
        intra = get_intraday_bars(sym, start, today.isoformat(), "1min")
        daily = polygon(f"/v2/aggs/ticker/{sym.upper()}/range/1/day/{start}/{today.isoformat()}",
                        {"adjusted": "true", "sort": "asc", "limit": 120})
        if "error" in intra or not (daily or {}).get("results"):
            continue
        by_day = group_rth_by_day(intra["bars"])
        # … so today's bars come from FMP whenever Polygon didn't include them.
        today_bars = by_day.get(today.isoformat()) or rth_only(
            fmp_intraday_bars(sym, today.isoformat()), today)
        prior = [d for d in sorted(by_day) if d != today.isoformat()][-baseline_days:]

        def first5_vol(day_bars):
            first_ts = int(day_bars[0]["timestamp"])
            return sum(float(b["volume"]) for b in day_bars
                       if int(b["timestamp"]) < first_ts + 5 * 60 * 1000)

        base = [first5_vol(by_day[d]) for d in prior if by_day[d]]
        if not base or not today_bars:
            continue
        rvol = first5_vol(today_bars) / (sum(base) / len(base)) if sum(base) else 0

        # Exclude today's partial daily bar by date — on the blocked tier it's
        # simply absent, and the old [:-1] slice would have dropped yesterday.
        dbars = [{"high": r["h"], "low": r["l"], "close": r["c"], "timestamp": r["t"]}
                 for r in daily["results"]
                 if to_et(int(r["t"])).date() != today]
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
    """Stage 1 + stage 2 in one call. ~1 + 2-3×scan_top_n API calls."""
    coarse = scan_market(top_n=scan_top_n)
    return refine_candidates([c["symbol"] for c in coarse],
                             min_rvol=min_rvol, top_n=top_n)
