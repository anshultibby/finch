---
name: kalshi_trading
description: Trade on Kalshi prediction markets (CFTC-regulated exchange). Authenticated HTTP client for the full Kalshi REST API — browse markets, check portfolio, place/cancel orders, get historical data.
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

Authenticated HTTP client for the Kalshi REST API. Handles RSA-PS256 signing automatically.

**Full API docs: https://docs.kalshi.com**
**Base URL (handled automatically): `https://api.elections.kalshi.com/trade-api/v2`**

```python
from kalshi_trading.scripts.kalshi import get, get_all, post, delete
# In strategy files: from finch import kalshi
```

Returns `{"error": "..."}` if credentials are missing. API errors raise `RuntimeError`.

---

## CRITICAL: Read this before searching for markets

### 1. ALWAYS paginate — use `get_all()` for list endpoints

`get()` returns ONE page. If you use `get()` on `/events` or `/markets`, you will miss results. Use `get_all()` instead — it auto-paginates and returns the complete list.

```python
# WRONG — only gets first page, misses results:
r = kalshi.get("/events", {"status": "open", "with_nested_markets": True})

# RIGHT — gets ALL pages automatically:
all_events = kalshi.get_all("/events", {"status": "open", "with_nested_markets": True})
# Returns: list of all event dicts (not wrapped in {"events": ...})
```

`get_all(path, params, collection_key=None, max_pages=20)` auto-detects the collection key from the path (`events`, `markets`, `market_positions`, `orders`, `fills`). Override with `collection_key` if needed.

Use plain `get()` only for single-item lookups like `get("/markets/TICKER")` or `get("/portfolio/balance")`.

### 2. Game-day sports markets are HIDDEN

Standard `/events` and `/markets` queries **DO NOT return game-day sports markets** (NBA, NHL, MLB, etc.). They are invisible unless you filter by their specific `series_ticker`.

**If you search `/events` or `/markets` without `series_ticker`, you will NOT find any sports games. This is by design in Kalshi's API.**

To find sports game markets, you MUST query with the sport's series ticker:

```python
# NBA games today
nba = kalshi.get_all("/events", {"series_ticker": "KXNBAGAME", "status": "open", "with_nested_markets": True})

# NHL games today
nhl = kalshi.get_all("/events", {"series_ticker": "KXNHLGAME", "status": "open", "with_nested_markets": True})

# You can also use /markets with series_ticker
markets = kalshi.get_all("/markets", {"series_ticker": "KXNBAGAME", "status": "open"})
```

**Known game-day series tickers:**

| Series ticker | Sport |
|---------------|-------|
| `KXNBAGAME` | NBA games |
| `KXNHLGAME` | NHL games |
| `KXMLBGAME` | MLB games |
| `KXNFLGAME` | NFL games |
| `KXNCAABGAME` | College basketball |
| `KXNCAAFGAME` | College football |
| `KXWBCGAME` | World Baseball Classic |
| `KXVALORANTGAME` | Valorant matches |
| `KXCSGOGAME` | Counter-Strike 2 |
| `KXLOLGAME` | League of Legends |

This list may be incomplete. New game series are added over time. If you're looking for a sport not listed, try guessing the pattern (`KX<SPORT>GAME`) or use `web_search("Kalshi [sport] markets")`.

Championship/futures series (e.g. `KXNBA`, `KXMLB`) are DIFFERENT from game-day series (`KXNBAGAME`, `KXMLBGAME`). Championship series have "who will win the title" markets, not individual game markets.

### 3. Game-day market timestamps are unreliable

Game-day sports events often have `None` for `expected_expiration_time` and `mutually_exclusive_end_time`. Do NOT rely on these fields for date filtering. Instead, get the `close_time` from individual markets within the event.

---

## API structure

Data is organized: **Series -> Events -> Markets**.

- **Series** — a recurring category (e.g. "NHL Games"). Identified by `series_ticker` (e.g. `KXNHLGAME`).
- **Event** — a specific instance (e.g. "Senators vs Canucks, Mar 9"). Contains one or more markets.
- **Market** — a single yes/no contract (e.g. "Will the Senators win?"). Identified by `ticker`.

**There is no text search endpoint.** Browse events by `series_ticker`, timestamps, or status.

**Ticker format:** `SERIES-EVENTDETAILS-OUTCOME`
```
Series:  KXNHLGAME
Event:   KXNHLGAME-26MAR09OTTVAN
Market:  KXNHLGAME-26MAR09OTTVAN-OTT
```

---

## API Endpoints

### Events

```python
# Browse events (with markets nested inside) — use get_all()
kalshi.get_all("/events", {"status": "open", "with_nested_markets": True})
# Returns: [{event_ticker, series_ticker, title, sub_title, category, mutually_exclusive, markets: [...]}, ...]

# Filter by series (REQUIRED for sports)
kalshi.get_all("/events", {"series_ticker": "KXNBAGAME", "status": "open", "with_nested_markets": True})

# Filter by close time
import time
tomorrow = int(time.time()) + 86400
kalshi.get_all("/events", {"status": "open", "min_close_ts": int(time.time()), "max_close_ts": tomorrow, "with_nested_markets": True})

# Single event by ticker (use get(), not get_all())
kalshi.get("/events/EVENT_TICKER", {"with_nested_markets": True})
# Returns: {event: {..., markets: [...]}}
```

**Event params:** `limit` (max 200), `cursor`, `status` (open|closed|settled), `series_ticker`, `with_nested_markets`, `min_close_ts`, `max_close_ts`, `min_updated_ts`

### Markets

```python
# All open markets in a series
kalshi.get_all("/markets", {"status": "open", "series_ticker": "KXNBAGAME"})

# Fetch specific markets by ticker
kalshi.get("/markets", {"tickers": "TICKER1,TICKER2,TICKER3"})

# Single market — full details including settlement rules
kalshi.get("/markets/MARKET_TICKER")
# Returns: {market: {ticker, event_ticker, title, yes_bid, yes_ask, no_bid, no_ask,
#           last_price, volume, open_interest, close_time, rules_primary, ...}}

# Orderbook
kalshi.get("/markets/MARKET_TICKER/orderbook", {"depth": 10})

# Candlesticks (price history)
kalshi.get("/markets/MARKET_TICKER/candlesticks", {"period_interval": 60, "start_ts": ..., "end_ts": ...})

# Series metadata
kalshi.get("/series/SERIES_TICKER")
```

**Market params:** `limit` (max 1000), `cursor`, `status` (unopened|open|closed|settled), `event_ticker`, `series_ticker`, `tickers` (comma-separated), `min_close_ts`, `max_close_ts`, `min_created_ts`, `max_created_ts`, `mve_filter` (only|exclude)

**Key fields:** `rules_primary` = settlement criteria (always read before trading). `yes_bid`/`yes_ask` in cents (0-100 = probability). `close_time` = when trading ends.

### Portfolio

```python
kalshi.get("/portfolio/balance")
# Returns: {balance: cents, portfolio_value: cents}

kalshi.get_all("/portfolio/positions", {"count_filter": "position"})
# Returns: [{ticker, position, market_exposure, realized_pnl, ...}, ...]
# position > 0 = YES, < 0 = NO
```

### Trading

```python
# Place order
kalshi.post("/portfolio/orders", {
    "ticker": "KXNHLGAME-26MAR09OTTVAN-OTT",
    "side": "yes",       # "yes" or "no"
    "action": "buy",     # "buy" or "sell"
    "count": 10,         # number of contracts
    "type": "market",    # "market" or "limit"
    # "yes_price": 45,   # cents, required for limit orders on yes side
    # "no_price": 55,    # cents, required for limit orders on no side
})

# View orders
kalshi.get_all("/portfolio/orders", {"status": "resting"})

# Cancel order
kalshi.delete("/portfolio/orders/ORDER_ID")

# Trade history (fills)
kalshi.get_all("/portfolio/fills")
kalshi.get_all("/portfolio/fills", {"ticker": "SOME-TICKER"})
# Returns: [{fill_id, order_id, ticker, side, action, count, yes_price, no_price, is_taker, created_time}, ...]
```

### Historical Data

Markets/fills/orders older than ~3 months move to historical endpoints:

```python
kalshi.get("/historical/cutoff")
kalshi.get_all("/historical/markets", {"series_ticker": "SOME_SERIES"})
kalshi.get("/historical/markets/TICKER")
kalshi.get_all("/historical/fills")
```

## Discovering series tickers

For non-game markets (politics, economics, etc.), browse open events:
```python
all_events = kalshi.get_all("/events", {"status": "open", "with_nested_markets": True})
series = {e["series_ticker"]: e["title"] for e in all_events if e.get("series_ticker")}
for st, title in sorted(series.items()):
    print(f"{st}: {title}")
# NOTE: This will NOT return game-day series — use the table above for those
```

If you suspect a series ticker exists:
```python
kalshi.get("/series/KXNBAGAME")
```

## Trading Safety

**If you are a bot, use `place_trade()` tool to place orders — do NOT call kalshi.post("/portfolio/orders") directly.**
The `place_trade()` tool automatically tracks trades, manages positions, and handles capital.
Only use the Kalshi API directly for research (reading markets, events, portfolio, fills).

**Always confirm with the user before placing, canceling, or modifying any order.** Show them the market ticker, side, action, count, price, and total cost before executing.

## Risk Guidelines

- Never bet more than 5% of balance on a single market
- Prefer markets with high open interest (easier to exit)
- Always read `rules_primary` before trading — it defines exactly how the market settles
- Limit orders are safer than market orders in thin markets
