---
name: polymarket
description: Browse and research Polymarket prediction markets — search events, get live prices, and compare with other exchanges. Use when working with Polymarket, checking prediction market prices, researching sports game odds, or finding arbitrage opportunities against Kalshi.
homepage: https://polymarket.com
metadata:
  emoji: "🔮"
  category: trading
  is_system: true
  requires: {}
---

# Polymarket Skill

Read-only market data from Polymarket. No credentials required.

Prices are **floats in [0, 1]** (e.g. `0.515` = 51.5¢).

## Import

```python
from skills.polymarket.scripts.polymarket import (
    get_events, get_sport_events, get_event,
    get_orderbook, get_prices,
)
```

## Browse Markets

```python
# General events (politics, crypto, etc.) — non-restricted
events = get_events(tag_slug="crypto", limit=20)
for e in events['events']:
    print(f"{e['slug']}: vol24h=${e['volume24hr']:.0f}")
    for m in e['markets']:
        print(f"  {m['question']}: {m['outcomes']}")

# Sports GAME markets — use this, not get_events()
# Standard tag queries hide game markets because they're restricted=True (US geo-block)
# get_sport_events() handles that automatically
nhl_games = get_sport_events("nhl", limit=50)
nba_games = get_sport_events("nba", limit=50)
nfl_games = get_sport_events("nfl", limit=50)

for e in nhl_games['events']:
    print(f"{e['slug']} | ends {e['end_date']} | vol24h=${e['volume24hr']:.0f}")
    for m in e['markets']:
        print(f"  {m['outcomes']}")  # e.g. {"Red Wings": 0.515, "Predators": 0.485}
```

## Get a Specific Event

```python
# Look up by slug — works for both restricted and non-restricted events
event = get_event("nhl-det-nsh-2026-03-02")
print(event['title'])
for m in event['markets']:
    print(f"  condition_id: {m['condition_id']}")
    print(f"  prices: {m['outcomes']}")
```

## Live Orderbook Prices

```python
# Get full orderbook data for a market using its condition_id
ob = get_orderbook("0xb529f668ece4bca3d05ed34864e04d30f41061a1779522585957ec01085bbc43")
print(ob['outcomes'])        # {"Red Wings": 0.515, "Predators": 0.485}
print(ob['accepting_orders'])  # True if market is live

# Just prices
prices = get_prices("0xb529f668ece4bca3d05ed34864e04d30f41061a1779522585957ec01085bbc43")
# {"Red Wings": 0.515, "Predators": 0.485}
```

## The Restricted Market Problem

Polymarket sports game markets are marked `restricted: true` for US geo-compliance.
This means:

- They **do not appear** in `get_events(tag_slug="nhl")` or similar broad queries
- They **do appear** if you query by exact slug or use `get_sport_events()`
- The CLOB API also works fine if you know the `condition_id`

The `get_sport_events()` function works around this by fetching and filtering for
restricted events that match the game slug pattern (`{sport}-{away}-{home}-{yyyy}-{mm}-{dd}`).

## Sports Slug Format

```
{sport}-{away_abbr}-{home_abbr}-{yyyy}-{mm}-{dd}

Examples:
  nhl-det-nsh-2026-03-02   (Detroit @ Nashville)
  nhl-cbj-nyr-2026-03-02   (Columbus @ NY Rangers)
  nba-lal-bos-2026-03-05   (Lakers @ Celtics)
```

## Cross-Exchange Comparison (Polymarket vs Kalshi)

```python
from skills.polymarket.scripts.polymarket import get_sport_events, get_prices
from skills.kalshi_trading.scripts.kalshi import get_events

# Get today's NHL games from both exchanges
pm_games = get_sport_events("nhl", limit=50)
kalshi_games = get_events(limit=100, status="open", series_ticker="KXNHLGAME")

# Polymarket prices are 0–1 floats; Kalshi prices are 0–100 cents
# To compare: multiply Polymarket price by 100

for e in pm_games['events']:
    for m in e['markets']:
        pm_prices = m['outcomes']  # e.g. {"Red Wings": 0.515}
        # Find matching Kalshi market and compare
```

### Arbitrage check
If the sum of the best prices for each outcome across both exchanges < 1.0,
a risk-free profit exists. Example:

```
Polymarket: Red Wings 0.515  →  buy Predators at 0.485
Kalshi:     Nashville  47¢   →  buy Nashville YES at $0.47
Combined cost: 0.485 + 0.47 = $0.955
Guaranteed payout: $1.00
Profit: $0.045 per dollar (4.5%)
```

Always account for fees, minimum order sizes ($5 on Polymarket CLOB), and execution risk.
