---
name: marketdata
description: Options data from MarketData.app — real-time chains & quotes with Greeks (delta/gamma/theta/vega) and implied volatility, plus historical EOD prices/OI/volume back to 2005 (historical Greeks/IV not included on current plan), expirations, and strikes. Use for live options quotes, chains, Greeks, and historical options price backtesting.
homepage: https://www.marketdata.app/docs/api
metadata:
  emoji: "🟢"
  category: options_data
  is_system: true
  auto_on: true
  requires:
    env:
      - MARKETDATA_API_KEY
    bins: []
---

# MarketData.app Options Skill

Real-time **and** historical options data with Greeks and implied volatility
already computed. Live quotes are real-time with an OPRA entitlement, otherwise
15-minute delayed. Historical end-of-day data goes back to **2005**.

**What it has:** chains, per-contract quotes, open interest, volume, bid/ask,
expirations, strikes — live or for any past trading day via a `date` param.
**Live** requests also include Greeks (delta, gamma, theta, vega) and IV.

**What it does NOT have:**
- **Historical Greeks/IV** — on the current plan, dated requests return prices/OI/
  volume but Greeks and IV come back `null`. Only *live* requests carry Greeks/IV.
  (A higher MarketData plan tier may unlock historical Greeks — verify with them.)
- rho, IV rank/percentile, IV surface, skew, or term-structure analytics.
- Corporate-action adjustment — historical prices are as-traded.

## Import Pattern

```python
from skills.marketdata.scripts.options import (
    get_options_chain,
    get_option_quote,
    get_expirations,
    get_strikes,
)
```

## Options Chain (live)

```python
from skills.marketdata.scripts.options import get_options_chain

# ~30 DTE ATM calls, filtered by delta
chain = get_options_chain("AAPL", dte=30, side="call", delta=".40-.60")
for c in chain:
    print(f"{c['optionSymbol']} strike={c['strike']} "
          f"delta={c['delta']:.2f} iv={c['iv']:.1%} "
          f"bid/ask={c['bid']}/{c['ask']} OI={c['openInterest']}")

# Each record: optionSymbol, underlying, expiration (epoch), expiration_date (ISO),
#   side, strike, dte, bid, bidSize, ask, askSize, mid, last,
#   volume, openInterest, underlyingPrice, inTheMoney,
#   intrinsicValue, extrinsicValue, iv, delta, gamma, theta, vega
```

Useful filters: `strike` (`300`, `>300`, `300-320`), `delta` (single or interval
`.40-.60`), `range` (`itm`/`otm`/`all`), `expiration` (`"2026-09-18"` or `"all"`),
`from_date`/`to_date` (expiration range), `strike_limit`, `min_open_interest`,
`min_volume`. Note: `dte` is a single closest-match value, not a range — use
`from_date`/`to_date` to span expirations.

## Options Chain (historical EOD)

Pass `date` for an end-of-day snapshot from any past trading day, back to 2005.
Dated responses are immutable and cached permanently. Note: on the current plan
historical rows carry prices/OI/volume but **`iv` and the Greeks are `null`** —
compute them yourself (Black-Scholes) if you need historical Greeks.

```python
# AAPL chain prices as of 2025-06-02 (Greeks will be null historically)
chain = get_options_chain("AAPL", date="2025-06-02", expiration="2025-07-18", side="call")
```

## Per-Contract Quote

```python
from skills.marketdata.scripts.options import get_option_quote

# Live snapshot for a single OCC symbol
q = get_option_quote("AAPL260918C00300000")

# Historical time series for that contract
hist = get_option_quote("AAPL260918C00300000", from_date="2025-01-01", to_date="2025-06-30")
```

## Expirations & Strikes

```python
from skills.marketdata.scripts.options import get_expirations, get_strikes

expirations = get_expirations("AAPL")          # ["2026-08-05", "2026-08-07", ...]
strikes = get_strikes("AAPL", expiration="2026-09-18")   # {expiration: [strikes...]}
```

## Low-Level Client

For any endpoint not wrapped above (e.g. quotes, lookup):

```python
from skills.marketdata.scripts._client import call_marketdata, records_from

data = call_marketdata("/v1/options/chain/TSLA/", {"dte": 30, "side": "put"})
if data["s"] == "ok":
    records = records_from(data)   # zip columnar arrays into list-of-dicts
```

The `date` param triggers permanent DB caching (historical is immutable); live
calls are cached in-memory for 60s. Every response has a status field `s`
(`ok` | `no_data` | `error`).

## Credit Cost (be economical)

MarketData bills by API credits: **real-time = 1 credit per option symbol**
returned, **historical = 1 credit per 1,000 symbols**. So a full live chain can
cost many credits — use `strike_limit`, `delta`, `dte`, or `expiration` filters
to fetch only the contracts you need. Historical/backtesting is very cheap.

## When to Use

- Live or 15-min-delayed options quotes, chains, Greeks, or IV
- "What is this contract trading at right now?"
- Historical EOD options data for backtesting a strategy (with Greeks/IV)
- Combine with **polygon_io** for underlying stock prices and **robinhood** for execution

## When NOT to Use

- You need IV rank/percentile, IV surface, skew, or term structure (not provided)
- You need rho (not exposed)
- You need corporate-action-adjusted historical option prices
