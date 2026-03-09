---
name: kalshi_trading
description: Trade on Kalshi prediction markets (CFTC-regulated exchange). Check portfolio, search markets, place/cancel orders. Use when working with Kalshi API, trading binary contracts, or managing prediction market positions.
homepage: https://kalshi.com/docs/api
metadata:
  emoji: "📈"
  category: trading
  is_system: true
  requires:
    env:
      - KALSHI_API_KEY_ID
      - KALSHI_PRIVATE_KEY
    bins:
      - cryptography
---

# Kalshi Trading Skill

Trade on Kalshi prediction markets. Requires Kalshi API credentials in Settings > API Keys.

Prices are in **CENTS** (0–100). Quantities are **integer contracts**.

## Import

**In strategy files (`strategy.py`)** — import from `finch`, not directly from this skill:

```python
# ✅ In strategy.py — read-only API, return actions instead of placing orders
from finch import kalshi, positions, log, state

def run():
    actions = []
    # Read market data
    markets = kalshi.get_markets(status="open", series_ticker="KXNHLGAME")
    for m in markets["markets"]:
        if m["yes_ask"] < 40:
            actions.append({"action": "buy", "market": m["ticker"], "side": "yes", "amount_usd": 5})
            break

    # Check open positions
    for pos in positions.open():
        mkt = kalshi.get_market(pos["market"])
        bid = mkt.get("yes_bid", 0)
        if bid >= 90:
            actions.append({"action": "sell", "position_id": pos["id"], "reason": "profit_target"})
    return actions
```

**In chat / bash / code execution** — direct import (full read+write access):

```python
from kalshi_trading.scripts.kalshi import (
    get_portfolio, get_balance, get_positions,
    get_events, get_markets, get_market, get_orderbook,
    place_order, get_orders, cancel_order,
    # Historical (data older than ~3 months)
    get_historical_cutoff,
    get_historical_markets, get_historical_market,
    get_historical_candlesticks,
    get_historical_fills, get_historical_orders,
)
```

## Portfolio

```python
# Full overview (balance + positions)
p = get_portfolio()
print(f"Cash: ${p['balance']:.2f}, Exposure: ${p['portfolio_value']:.2f}")
for pos in p['positions']:
    print(f"  {pos['ticker']}: {pos['position']} contracts")

# Just balance
b = get_balance()  # {balance, portfolio_value}

# Just positions
p = get_positions(limit=100)  # {positions, count}
```

## Browse Markets

```python
# Get open events (each event groups related markets)
events = get_events(limit=20, status="open")
for event in events['events']:
    print(f"\n{event['event_ticker']}: {event['title']}")
    for market in event.get('markets', []):
        print(f"  {market['ticker']}: Yes {market['yes_bid']}¢/{market['yes_ask']}¢")

# Filter by series — use the series_ticker param
nba = get_events(limit=100, status="open", series_ticker="KXNBA")
nhl = get_events(limit=100, status="open", series_ticker="KXNHLGAME")
nfl = get_events(limit=100, status="open", series_ticker="KXNFL")

# Flat market list (no event grouping) — also supports series_ticker
markets = get_markets(limit=50, status="open")
nhl_markets = get_markets(limit=100, status="open", series_ticker="KXNHLGAME")

# Get a specific market
m = get_market("KXBTC-26FEB28-W100")
print(f"{m['ticker']}: Yes {m['yes_bid']}¢ bid / {m['yes_ask']}¢ ask")
print(f"Volume: {m['volume']:,}  OI: {m['open_interest']:,}")

# Get orderbook depth
ob = get_orderbook("KXBTC-26FEB28-W100", depth=5)
# ob['yes'] = [[price, size], ...]  ob['no'] = [[price, size], ...]
```

## Trading

```python
# Market buy — 10 YES contracts
order = place_order(ticker="KXBTC-26FEB28-W100", side="yes", action="buy", count=10)

# Limit buy — 10 YES at 45¢
order = place_order(ticker="KXBTC-26FEB28-W100", side="yes", action="buy",
                    count=10, order_type="limit", price=45)

# Sell
order = place_order(ticker="KXBTC-26FEB28-W100", side="yes", action="sell", count=5)

# View open orders
orders = get_orders(status="resting")  # or "executed", "canceled"

# Cancel
cancel_order(order_id="abc123")
```

## Error Handling

All functions return `{"error": "..."}` on failure — check before using the result:

```python
result = get_market("INVALID-TICKER")
if "error" in result:
    print(f"Failed: {result['error']}")
```

## Common Workflows

### Check account then trade
1. `get_portfolio()` — see balance and open positions
2. `get_events(status="open")` — find a market
3. `get_market(ticker)` — check current prices
4. `place_order(...)` — execute
5. `get_orders(status="resting")` — confirm

### Manage a position
1. `get_positions()` — find position
2. `get_market(ticker)` — check current price vs entry
3. `place_order(action="sell", ...)` — close if needed

## Sports Market Series Tickers

Sports markets require `series_ticker` — they won't appear in general searches since titles use team names, not sport names.

| Sport | series_ticker |
|-------|--------------|
| NHL   | `KXNHLGAME`  |
| NBA   | `KXNBA`      |
| NFL   | `KXNFL`      |

### NHL ticker format
```
Event:  KXNHLGAME-[YYMMMDD][AWAY][HOME]        e.g. KXNHLGAME-26FEB28PITNYR
Market: KXNHLGAME-[YYMMMDD][AWAY][HOME]-[TEAM]  e.g. KXNHLGAME-26FEB28PITNYR-PIT
```
Each game has two markets (one per team). The URL on kalshi.com uses the event ticker; add the team suffix to get a tradeable market ticker.

## Historical Data

Kalshi partitions data older than ~3 months into historical endpoints. Use `get_historical_cutoff()` to find the boundary.

```python
from kalshi_trading.scripts.kalshi import (
    get_historical_cutoff,
    get_historical_markets, get_historical_market,
    get_historical_candlesticks,
    get_historical_fills, get_historical_orders,
)

# Step 1: check the cutoff dates
cutoff = get_historical_cutoff()
# cutoff["market_settled_ts"] — markets settled before this → use historical endpoints
# cutoff["trades_created_ts"] — fills before this → use historical endpoints
# cutoff["orders_updated_ts"] — orders before this → use historical endpoints

# Settled markets older than the cutoff
old_markets = get_historical_markets(limit=100, series_ticker="KXNBA")
for m in old_markets["markets"]:
    print(f"{m['ticker']}: settled {m['close_time']}, value={m['settlement_value']}")
# Paginate with cursor
next_page = get_historical_markets(cursor=old_markets["cursor"])

# Single historical market
m = get_historical_market("KXNBA-26FEB15-LAL")

# OHLC candlestick data for a historical market
import time
candles = get_historical_candlesticks(
    "KXNBA-26FEB15-LAL",
    start_ts=int(time.time()) - 86400 * 30,  # 30 days ago
    period_interval=60,  # 1-hour candles
)
for c in candles["candles"]:
    print(f"  {c['ts']}: O={c['open']} H={c['high']} L={c['low']} C={c['close']}")

# Historical fills (trades you made, older than cutoff)
old_fills = get_historical_fills(ticker="KXNBA-26FEB15-LAL", limit=50)
for f in old_fills["fills"]:
    print(f"{f['trade_id']}: {f['action']} {f['count']}x {f['ticker']} @ {f['yes_price']}¢")

# Historical orders (older than cutoff — resting orders always in get_orders())
old_orders = get_historical_orders(limit=100)
```

> **Migration note (after March 6, 2026):** The standard live endpoints (`get_markets`, `get_orders`, `get_fills` via portfolio) no longer return data older than the cutoff. Always check `get_historical_cutoff()` and route to the historical endpoints accordingly.

## Risk Guidelines

- Never bet more than 5% of balance on a single market
- Prefer markets with high open interest (easier to exit)
- Always check resolution criteria before trading
- Limit orders are safer than market orders in thin markets
