---
name: polymarket
description: Browse and research Polymarket prediction markets — search events, get live prices, track top traders, view leaderboards, and compare with other exchanges. Read-only, no credentials needed.
homepage: https://polymarket.com
metadata:
  emoji: "🔮"
  category: trading
  is_system: true
  requires: {}
---

# Polymarket Skill

Read-only market data from Polymarket. No credentials required.

This skill exposes three HTTP helpers — `gamma()`, `clob()`, `data()` — one for each Polymarket API. All return raw JSON.

**Prices are floats in [0, 1]** (e.g. `0.515` = 51.5¢). Multiply by 100 to compare with Kalshi cents.

## Usage

```python
from polymarket.scripts.polymarket import gamma, clob, data, get_sport_events, parse_outcomes
```

In strategy files:
```python
from finch import polymarket
response = polymarket.gamma("/events", {"limit": 50, "active": "true", "tag_slug": "nba"})
```

## The three APIs

| Function | Base URL | Purpose |
|----------|----------|---------|
| `gamma(path, params)` | `gamma-api.polymarket.com` | Events, markets, profiles, search |
| `clob(path, params)` | `clob.polymarket.com` | Live orderbook, market trades |
| `data(path, params)` | `data-api.polymarket.com` | Leaderboard, trader positions/trades/activity, holders |

## Gamma API — Events & Markets

### Browse events

```python
# Active events by category
gamma("/events", {"limit": 50, "active": "true", "closed": "false"})
gamma("/events", {"limit": 50, "active": "true", "closed": "false", "tag_slug": "crypto"})
gamma("/events", {"limit": 50, "active": "true", "closed": "false", "tag_slug": "politics"})
# → list of event dicts

# Pagination: use offset
gamma("/events", {"limit": 100, "offset": 100, "active": "true", "closed": "false"})

# Resolved/settled events
gamma("/events", {"limit": 50, "closed": "true", "active": "false", "tag_slug": "nhl"})

# Single event by slug
gamma("/events", {"slug": "nhl-det-nsh-2026-03-02"})
```

Each event contains a `markets` array. Market outcomes and prices are JSON strings inside JSON — use `parse_outcomes(market)` to decode them:

```python
events = gamma("/events", {"limit": 10, "active": "true", "closed": "false"})
for e in events:
    print(f"{e['slug']}: {e['title']}")
    for m in (e.get('markets') or []):
        prices = parse_outcomes(m)  # {"Yes": 0.72, "No": 0.28} or {"Team A": 0.55, "Team B": 0.45}
        print(f"  {m['question']}: {prices}")
        print(f"  condition_id: {m['conditionId']}")  # needed for CLOB/Data API calls
```

Key event fields: `id`, `slug`, `title`, `endDate`, `volume24hr`, `liquidity`, `restricted`, `markets[]`

Key market fields: `id`, `slug`, `question`, `conditionId`, `outcomes` (JSON string), `outcomePrices` (JSON string), `volume`, `liquidity`

### Search

```python
# Search events and markets by keyword
gamma("/public-search", {"q": "bitcoin", "limit_per_type": 10})
# → {events: [...], profiles: [...]}

# Include trader profiles in search
gamma("/public-search", {"q": "whale", "limit_per_type": 5, "search_profiles": "true"})
```

### Trader profiles

```python
gamma("/public-profile", {"address": "0x7c3db723f1d4d8cb9c550095203b686cb11e5c6b"})
# → {name, pseudonym, bio, proxyWallet, profileImage, xUsername, verifiedBadge, createdAt}
```

## CLOB API — Orderbook & Trades

```python
# Live orderbook for a market (use conditionId from Gamma response)
clob("/markets/CONDITION_ID")
# → {condition_id, question, tokens: [{outcome, price}, ...], accepting_orders, minimum_order_size, game_start_time, ...}

# Public trade history
clob("/trades", {"market": "CONDITION_ID", "limit": 100})
# → list of trades or {data: [...]}
# Each trade: {id, outcome, price, size, timestamp}
```

## Data API — Leaderboard & Trader Analytics

### Leaderboard

```python
data("/v1/leaderboard", {
    "category": "OVERALL",   # OVERALL, POLITICS, SPORTS, CRYPTO, CULTURE, WEATHER, ECONOMICS, TECH, FINANCE
    "timePeriod": "ALL",     # DAY, WEEK, MONTH, ALL
    "orderBy": "PNL",        # PNL or VOL
    "limit": 25,
    "offset": 0,
})
# → list of trader dicts
# Each: {rank, proxyWallet, userName, pnl, vol, profileImage, xUsername, verifiedBadge}
```

### Trader positions

```python
data("/positions", {
    "user": "0xWALLET",
    "limit": 100,
    "offset": 0,
    "sortBy": "CURRENT",       # CURRENT, INITIAL, TOKENS, CASHPNL, PERCENTPNL, TITLE, PRICE, AVGPRICE
    "sortDirection": "DESC",   # ASC or DESC
})
# → list of position dicts
# Each: {conditionId, title, outcome, size, avgPrice, initialValue, currentValue, cashPnl, percentPnl, slug, eventSlug}
```

### Trader trades

```python
data("/trades", {
    "user": "0xWALLET",
    "limit": 100,
    "offset": 0,
    # "market": "CONDITION_ID",  # optional filter
})
# → list of trade dicts
# Each: {conditionId, title, outcome, side, price, size, timestamp, slug, eventSlug}
```

### Trader activity

```python
data("/activity", {
    "user": "0xWALLET",
    "limit": 100,
    "offset": 0,
    # "type": "TRADE",  # optional: TRADE, SPLIT, MERGE, REDEEM, REWARD, CONVERSION, MAKER_REBATE
})
# → list of activity dicts
# Each: {type, conditionId, title, outcome, side, price, size, usdcSize, timestamp, slug, eventSlug}
```

### Market holders

```python
data("/holders", {"market": "CONDITION_ID", "limit": 20})
# → list of {token, holders: [{proxyWallet, amount, pseudonym, name, profileImage}]}
```

## Sports markets — the restricted quirk

Sports game markets are marked `restricted: true` for US geo-compliance. This means:

- They **do not appear** in standard `gamma("/events", {"tag_slug": "nhl"})` queries
- They **do appear** if you query by exact slug or use `get_sport_events()`
- The CLOB and Data APIs work fine if you have the `conditionId`

Use `get_sport_events(sport, limit)` to find them — it paginates and filters automatically:

```python
nhl_games = get_sport_events("nhl", limit=50)
nba_games = get_sport_events("nba", limit=50)
# → list of raw event dicts (same format as gamma("/events") response)

for e in nhl_games:
    print(f"{e['slug']}: {e['title']}")
    for m in (e.get('markets') or []):
        print(f"  {parse_outcomes(m)}")
```

Game slug format: `{sport}-{away}-{home}-{yyyy}-{mm}-{dd}` (e.g. `nhl-det-nsh-2026-03-02`)

## Pagination

Gamma and Data APIs use **offset-based pagination**:
```python
# Page through all events
all_events = []
offset = 0
while True:
    batch = gamma("/events", {"limit": 100, "offset": offset, "active": "true", "closed": "false"})
    if not batch:
        break
    all_events.extend(batch)
    if len(batch) < 100:
        break
    offset += 100
```

## Cross-exchange comparison (vs Kalshi)

```python
from polymarket.scripts.polymarket import get_sport_events, parse_outcomes, clob
from kalshi_trading.scripts.kalshi import get as kalshi_get

pm_games = get_sport_events("nhl", limit=50)
kalshi_games = kalshi_get("/events", {"limit": 100, "status": "open", "series_ticker": "KXNHLGAME", "with_nested_markets": True})

# Polymarket prices are 0–1 floats; Kalshi prices are 0–100 cents
# Multiply PM prices by 100 to compare
```

### Arbitrage check
If the sum of best prices for each outcome across exchanges < 1.0, a risk-free profit exists:
```
Polymarket: Red Wings 0.515  →  buy Predators at 0.485
Kalshi:     Nashville  47¢   →  buy Nashville YES at $0.47
Combined cost: 0.485 + 0.47 = $0.955
Payout: $1.00 → Profit: 4.5%
```
Account for fees, minimum order sizes ($5 on Polymarket CLOB), and execution risk.
