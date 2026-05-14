---
name: orats
description: End-of-day options analytics from ORATS — chains with Greeks, IV rank/percentile, IV surface, historical vol metrics, and summary stats. NOT real-time. Use for options research, vol analysis, earnings plays, and strategy selection.
homepage: https://docs.orats.io
metadata:
  emoji: "📈"
  category: options_data
  is_system: true
  requires:
    env:
      - ORATS_API_KEY
    bins: []
---

# ORATS Options Skill

End-of-day options analytics. **NOT real-time** — do not use for live price tracking or intraday monitoring.

- **"Current" endpoints** (`strikes`, `summaries`, `ivrank`, `monies/implied`): updated once daily, ~14 min before market close. During market hours, data reflects the **previous** close. After ~3:46pm ET, data reflects today.
- **Historical endpoints** (`hist/*`): full daily history back to 2007, cached permanently.

For real-time options quotes, use a different data source. ORATS is for **analysis and research**, not price monitoring.

## Import Pattern

```python
from skills.orats.scripts.options import (
    get_options_chain,
    get_iv_rank,
    get_historical_metrics,
    get_iv_surface,
    get_summary,
)
```

## Low-Level Client

For any ORATS endpoint not wrapped above, use the generic client:

```python
from skills.orats.scripts._client import call_orats

# call_orats(endpoint, params) → list of records
# Token is injected automatically. Historical endpoints (hist/*) are cached to DB permanently.
# Current endpoints are cached in-memory for 5 minutes.

# Examples:
data = call_orats("ivrank", {"ticker": "AAPL"})            # current IV rank
data = call_orats("hist/earnings", {"ticker": "AAPL"})      # earnings dates
data = call_orats("hist/divs", {"ticker": "TSLA"})          # dividend history
data = call_orats("hist/splits", {"ticker": "NVDA"})        # stock splits
data = call_orats("hist/hvs", {"ticker": "SPY"})            # historical volatility
data = call_orats("hist/dailies", {"ticker": "AAPL"})       # OHLCV price history
data = call_orats("cores", {"ticker": "AAPL"})              # full core analytics
data = call_orats("monies/forecast", {"ticker": "AAPL"})    # forecast vol surface
data = call_orats("strikes", {"ticker": "AAPL", "dte": "30-60", "delta": ".30-.70"})  # filtered chain
```

## Options Chain

Full end-of-day chain with Greeks, captured ~14 min before close.

```python
from skills.orats.scripts.options import get_options_chain

chain = get_options_chain("AAPL")
strikes = chain["strikes"]  # list of records, sorted by expiry then strike

# Each record has: strike, expirDate, dte, stockPrice,
#   delta, gamma, theta, vega, rho, phi,
#   callBidPrice, callAskPrice, putBidPrice, putAskPrice,
#   callMidIv, putMidIv, smvVol,
#   callVolume, putVolume, callOpenInterest, putOpenInterest

# Filter to 30-45 DTE ATM calls
atm_calls = [s for s in strikes if 30 <= s["dte"] <= 45 and 0.40 <= s["delta"] <= 0.60]
for s in atm_calls:
    print(f"{s['expirDate']} {s['strike']}C: delta={s['delta']:.2f} IV={s['callMidIv']:.1%} bid/ask={s['callBidPrice']}/{s['callAskPrice']}")
```

## IV Rank & Percentile

How current IV compares to its own history. IV rank = where today sits in the range; IV percentile = % of days below today.

```python
from skills.orats.scripts.options import get_iv_rank

# Current snapshot
ivr = get_iv_rank("AAPL")
latest = ivr["history"][-1]
print(f"IV: {latest['iv']:.1%}, 1y Rank: {latest['ivRank1y']}, 1y Pctl: {latest['ivPct1y']}")

# Historical — find elevated vol periods for backtesting
import pandas as pd
ivr = get_iv_rank("AAPL", from_date="2023-01-01", to_date="2024-12-31")
df = pd.DataFrame(ivr["history"])
high_iv = df[df["ivRank1y"] > 50]
print(f"{len(high_iv)} days with IV rank > 50 (good for selling premium)")
```

## IV Surface

Implied vol at standardized moneyness levels across expirations — shows skew and term structure.

```python
from skills.orats.scripts.options import get_iv_surface

surface = get_iv_surface("AAPL")
# Each record: expirDate, dte, plus vol at 10 moneyness levels (vol100..vol0),
#   atmiv, slope, calVol, earnEffect

import pandas as pd
df = pd.DataFrame(surface["surface"])
# Term structure: ATM IV by expiration
print(df[["expirDate", "dte", "atmiv"]].to_string(index=False))

# Skew: compare OTM put vol to ATM vol
for _, row in df.iterrows():
    skew = row.get("vol100", 0) - row.get("atmiv", 0)  # vol100 = deep OTM put vol
    print(f"DTE {row['dte']}: ATM IV={row['atmiv']:.1%}, put skew={skew:+.1%}")
```

## Summary Stats

Current snapshot of IV term structure, skew, contango, earnings, and more.

```python
from skills.orats.scripts.options import get_summary

s = get_summary("AAPL")
print(f"30d IV: {s['iv30d']:.1%}  |  60d IV: {s['iv60d']:.1%}  |  90d IV: {s['iv90d']:.1%}")
print(f"Contango: {s.get('contango', 0):.3f}")  # >0 = normal term structure
print(f"Implied earnings move: {s.get('impliedMove', 'N/A')}")
print(f"IV rank 1y: {s.get('ivPctile1y', 'N/A')}")
```

## Historical Metrics (Core Data)

200+ fields per day going back to 2007: realized vol, IV term structure, skew, contango, earnings data, beta, correlation. The richest endpoint.

```python
from skills.orats.scripts.options import get_historical_metrics

import pandas as pd
metrics = get_historical_metrics("AAPL", from_date="2023-01-01", to_date="2024-12-31")
df = pd.DataFrame(metrics["history"])
df["tradeDate"] = pd.to_datetime(df["tradeDate"])

# Key fields: pxAtmIv, iv20d, iv30d, iv60d, iv90d, iv6m, iv1y,
#   orHv20d, orHv60d (realized vol), ivPctile1m, ivPctile1y,
#   slope, contango, nextErn, impliedEarningsMove,
#   beta1y, correlSpy1y, mktCap, sector
```

## Additional Endpoints via call_orats()

| Endpoint | Use Case |
|---|---|
| `hist/earnings` | Historical earnings dates and announcement times |
| `hist/divs` | Dividend history (ex-dates, amounts, frequency) |
| `hist/splits` | Stock split history |
| `hist/hvs` | Realized vol at multiple lookbacks (1d to 1000d) |
| `hist/dailies` | OHLCV price history |
| `cores` | Full core analytics (200+ fields, current day) |
| `hist/cores` | Same as historical_metrics wrapper |
| `monies/forecast` | Forecast vol surface (vs implied) |
| `hist/monies/implied` | Historical implied vol surface |
| `strikes/options` | Look up by OCC symbol (e.g. `AAPL  260620C00200000`) |
| `hist/strikes` | Historical chain for a specific date |

Pass `tradeDate` param for hist endpoints that support date-based queries. Use `fields` param to limit response size.

## When to Use This Skill

- User asks about options Greeks, IV levels, or an options chain (end-of-day)
- User wants to know if IV is high or low relative to history (IV rank/percentile)
- User asks about vol surface, skew, or term structure
- User is planning an earnings trade and wants historical implied move data
- User wants to backtest a vol-based strategy using daily data
- User asks about historical volatility vs implied volatility
- Combine with **polygon_io** for real-time stock prices and **alpaca** for trade execution

## When NOT to Use This Skill

- User wants real-time or live options quotes — ORATS data is end-of-day only
- User wants to track intraday options price movements
- User asks "what is X contract trading at right now" — this skill cannot answer that
- User needs tick-level or minute-level options data
