---
name: fred
description: "US macro data & the macro event calendar from the St. Louis Fed (FRED): CPI/PCE inflation, jobs, GDP, rates, yields, VIX — plus upcoming_events() for scheduled market-moving releases (CPI, NFP, FOMC, GDP...) with dates, ET times, and impact. Use for macro questions and for event-aware trading/automations."
metadata:
  emoji: "🏛️"
  category: data
  is_system: true
  requires:
    env:
      - FRED_API_KEY
    bins: []
---

# FRED — Macro Data & Event Calendar

```python
from skills.fred.scripts.series import latest, get_series, search_series, macro_snapshot, KEY_SERIES
from skills.fred.scripts.releases import upcoming_events, events_today
```

## The event calendar (the part automations care about)

```python
upcoming_events(days=7)
# [{"date": "2026-06-11", "event": "CPI", "time_et": "08:30", "impact": "high", ...},
#  {"date": "2026-06-17", "event": "FOMC rate decision", "time_et": "14:00", "impact": "high", ...}]
events_today()   # [] means a clear macro calendar today
```

Covers CPI, NFP/jobs report, PCE, GDP, PPI, retail sales, weekly claims (from
FRED's release calendar) + FOMC decision days (hardcoded schedule in
`releases.py` — update each December). Times are the standard conventions
(08:30 ET data drops, 14:00 ET FOMC); FRED publishes dates only.

## Series data

```python
latest("UNRATE")                       # {"date": "...", "value": 4.1}
latest("CPIAUCSL", units="pc1")        # CPI inflation, % vs year ago
get_series("DGS10", limit=30)          # 10y yield, last 30 obs (oldest→newest)
search_series("housing starts")        # find ids you don't know
macro_snapshot()                       # latest of all KEY_SERIES (~14 calls)
```

`KEY_SERIES` has the market movers pre-mapped: CPIAUCSL/CPILFESL (CPI),
PCEPILFE (core PCE — the Fed's gauge), PAYEMS (NFP), UNRATE, ICSA, GDPC1,
RSAFS, FEDFUNDS/DFEDTARU (policy rate), DGS2/DGS10/T10Y2Y (curve), VIXCLS.
For inflation series, always pass `units="pc1"` to get the % rate people mean.

Values arrive as data is *released* (CPI for May appears mid-June) — `latest()`
gives the freshest print, not today's economy. Check `"error"` keys on every
response.
