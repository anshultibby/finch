"""
Macro event calendar — when the market-moving numbers drop.

upcoming_events() merges two sources:
  1. FRED's release-dates calendar (CPI, NFP, GDP, PCE, PPI, retail sales,
     claims — scheduled data releases, matched by name).
  2. The FOMC meeting schedule (hardcoded yearly — it isn't a FRED release;
     the rate decision hits at 14:00 ET on day 2).

Times are the long-standing conventions (BLS/BEA/Census release at 08:30 ET;
FOMC decision 14:00 ET) — FRED only provides dates, not times.
"""
from datetime import date, timedelta
from typing import List, Dict, Any, Optional
from ._client import fred

# Substring match (lowercased) against FRED release names → (label, time_et, impact)
MARKET_MOVING = {
    "consumer price index":          ("CPI", "08:30", "high"),
    "employment situation":          ("NFP / jobs report", "08:30", "high"),
    "personal income and outlays":   ("PCE inflation", "08:30", "high"),
    "gross domestic product":        ("GDP", "08:30", "high"),
    "producer price index":          ("PPI", "08:30", "medium"),
    "advance monthly sales for retail": ("Retail sales", "08:30", "medium"),
    "unemployment insurance weekly claims": ("Initial claims", "08:30", "low"),
}

# FOMC meetings (decision = 14:00 ET on the SECOND day). Update each December
# from federalreserve.gov/monetarypolicy/fomccalendars.htm
FOMC_DECISION_DAYS = [
    # 2026
    "2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17",
    "2026-07-29", "2026-09-16", "2026-10-28", "2026-12-09",
]


def upcoming_events(days: int = 7, market_moving_only: bool = True,
                    today: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Scheduled macro events in the next `days`, soonest first:
        [{"date": "2026-06-11", "event": "CPI", "time_et": "08:30",
          "impact": "high", "release": "Consumer Price Index"}, ...]
    Pass market_moving_only=False for every FRED release (noisy).
    """
    start = date.fromisoformat(today) if today else date.today()
    end = start + timedelta(days=days)
    resp = fred("releases/dates",
                realtime_start=start.isoformat(), realtime_end=end.isoformat(),
                include_release_dates_with_no_data="true",
                sort_order="asc", limit=1000)
    events: List[Dict[str, Any]] = []
    if "error" not in resp:
        seen = set()
        for rd in resp.get("release_dates", []):
            d, name = rd.get("date", ""), rd.get("release_name", "")
            if not (start.isoformat() <= d <= end.isoformat()):
                continue
            if "research" in name.lower():   # e.g. "Research Consumer Price Index"
                continue
            matched = None
            for key, (label, time_et, impact) in MARKET_MOVING.items():
                if key in name.lower():
                    matched = {"date": d, "event": label, "time_et": time_et,
                               "impact": impact, "release": name}
                    break
            if matched and (d, matched["event"]) not in seen:
                seen.add((d, matched["event"]))
                events.append(matched)
            elif not matched and not market_moving_only:
                events.append({"date": d, "event": name, "time_et": None,
                               "impact": "unknown", "release": name})
    for f in FOMC_DECISION_DAYS:
        if start.isoformat() <= f <= end.isoformat():
            events.append({"date": f, "event": "FOMC rate decision", "time_et": "14:00",
                           "impact": "high", "release": "FOMC"})
    events.sort(key=lambda e: (e["date"], e["time_et"] or "99:99"))
    return events


def events_today(today: Optional[str] = None) -> List[Dict[str, Any]]:
    """Today's market-moving events (empty list = clear macro calendar)."""
    return [e for e in upcoming_events(days=0, today=today)
            if e["date"] == (today or date.today().isoformat())]
