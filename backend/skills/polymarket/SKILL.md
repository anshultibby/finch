---
name: polymarket
description: Browse and research Polymarket prediction markets — search events, get live prices, track top traders, view leaderboards, and compare with other exchanges. Use when working with Polymarket, checking prediction market prices, researching sports game odds, studying trader behavior, or finding arbitrage opportunities against Kalshi.
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
    # Event discovery
    get_events, get_sport_events, get_event, search_markets,
    # Orderbook & prices
    get_orderbook, get_prices,
    # Leaderboard & traders
    get_leaderboard, get_trader_profile,
    get_trader_positions, get_trader_trades, get_trader_activity,
    # Market holders
    get_market_holders,
    # Historical
    get_resolved_events, get_market_trades,
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

## Search Markets & Profiles

```python
# Search for markets by keyword
results = search_markets("bitcoin", limit=10)
for e in results['events']:
    print(f"{e['title']} — {e['slug']}")

# Also search for trader profiles
results = search_markets("whale", limit=5, include_profiles=True)
for p in results.get('profiles', []):
    print(f"{p['name']} — {p['proxy_wallet']}")
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

## Top Traders & Leaderboard

```python
# Get top traders by P&L (all time)
top = get_leaderboard(category="OVERALL", time_period="ALL", order_by="PNL", limit=25)
for t in top['traders']:
    print(f"#{t['rank']} {t['username']}: PnL=${t['pnl']:,.0f} Vol=${t['volume']:,.0f}")

# Top sports traders this week
sports_top = get_leaderboard(category="SPORTS", time_period="WEEK", order_by="PNL")

# Top crypto traders by volume this month
crypto_vol = get_leaderboard(category="CRYPTO", time_period="MONTH", order_by="VOL")

# Categories: OVERALL, POLITICS, SPORTS, CRYPTO, CULTURE, WEATHER, ECONOMICS, TECH, FINANCE
# Time periods: DAY, WEEK, MONTH, ALL
# Order by: PNL, VOL
```

## Trader Deep Dive

```python
# Get a trader's profile
profile = get_trader_profile("0x7c3db723f1d4d8cb9c550095203b686cb11e5c6b")
print(f"{profile['name']} (@{profile['x_username']})")

# See their current positions (sorted by value)
positions = get_trader_positions(
    "0x7c3db723f1d4d8cb9c550095203b686cb11e5c6b",
    sort_by="CURRENT",  # CURRENT, INITIAL, TOKENS, CASHPNL, PERCENTPNL, TITLE, PRICE, AVGPRICE
    limit=50,
)
for p in positions['positions']:
    print(f"  {p['title']} — {p['outcome']}: {p['size']:.1f} shares @ avg {p['avg_price']:.3f}")
    print(f"    PnL: ${p['cash_pnl']:.2f} ({p['percent_pnl']:.1f}%)")

# See their trade history
trades = get_trader_trades("0x7c3db723f1d4d8cb9c550095203b686cb11e5c6b", limit=50)
for t in trades['trades']:
    print(f"  {t['timestamp']}: {t['side']} {t['outcome']} @ {t['price']:.3f} x {t['size']:.1f}")

# Full activity feed (trades + redemptions + rewards etc.)
activity = get_trader_activity("0x7c3db723f1d4d8cb9c550095203b686cb11e5c6b", limit=50)
for a in activity['activities']:
    print(f"  {a['type']}: {a['title']} — ${a['usdc_size']:.2f}")
```

## Market Holders (Who Holds the Biggest Positions)

```python
# See who has the largest positions in a market
holders = get_market_holders("0xb529f668ece4bca3d05ed34864e04d30f41061a1779522585957ec01085bbc43")
for group in holders['holders']:
    print(f"Token: {group['token']}")
    for h in group['holders']:
        print(f"  {h['pseudonym'] or h['name']}: {h['amount']:.1f} shares")
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

## Historical Data

```python
# Resolved/settled events
past = get_resolved_events(tag_slug="nhl", limit=50)
for e in past['events']:
    print(f"{e['slug']} | ended {e['end_date']}")
    for m in e['markets']:
        print(f"  {m['question']}: {m['outcomes']}")  # 0.0 or 1.0 = settled outcome

# Public trade history for any market
trades = get_market_trades("0xb529f668ece4bca3d05ed34864e04d30f41061a1779522585957ec01085bbc43", limit=100)
for t in trades['trades']:
    print(f"{t['timestamp']}: {t['outcome']} @ {t['price']:.3f} x {t['size']:.2f}")
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

## Copy Trading Workflow

Use the leaderboard + trader positions to build a copy-trading strategy:

```python
# 1. Find top traders in your category
top = get_leaderboard(category="SPORTS", time_period="MONTH", order_by="PNL", limit=10)

# 2. Deep-dive their current positions
for t in top['traders']:
    positions = get_trader_positions(t['proxy_wallet'], sort_by="CURRENT", limit=20)
    print(f"\n{t['username']} (PnL: ${t['pnl']:,.0f}):")
    for p in positions['positions']:
        print(f"  {p['title']} — {p['outcome']} @ avg {p['avg_price']:.3f} (PnL: ${p['cash_pnl']:.2f})")

# 3. Monitor their recent trades for signals
for t in top['traders'][:3]:
    recent = get_trader_trades(t['proxy_wallet'], limit=10)
    print(f"\n{t['username']} recent trades:")
    for trade in recent['trades']:
        print(f"  {trade['side']} {trade['outcome']} @ {trade['price']:.3f}")
```
