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

```python
from skills.kalshi_trading.scripts.kalshi import get, get_all, post, delete
from skills.kalshi_trading.scripts.api_docs import lookup, schema
```

- `get(path, params)` — single-page GET (use for single-item lookups)
- `get_all(path, params)` — **auto-paginating GET** (use for all list endpoints)
- `post(path, body)` — POST (place orders, create combos)
- `delete(path)` — DELETE (cancel orders)
- `lookup(query)` — look up any API endpoint from the live OpenAPI spec
- `schema(name)` — look up response/request schemas with all field names

Returns `{"error": "..."}` if credentials are missing. API errors raise `RuntimeError`.

---

## Available API Endpoints

Use `lookup("endpoint")` for full details on any of these.

| Category | Endpoints | What you can do |
|---|---|---|
| **Exchange** | `/exchange/status`, `/exchange/schedule`, `/exchange/announcements` | Check if exchange is open, trading hours, outages |
| **Series** | `/series`, `/series/{ticker}` | Browse all series templates, categories, volume |
| **Discovery** | `/search/tags_by_categories`, `/search/filters_by_sport` | Find categories, tags, sport-specific filters |
| **Events** | `/events`, `/events/{ticker}`, `/events/{ticker}/metadata` | Browse/filter events, get nested markets |
| **MVE/Combos** | `/events/multivariate`, `/multivariate_event_collections` | Combo/parlay events and collections |
| **Markets** | `/markets`, `/markets/{ticker}`, `/markets/{ticker}/orderbook`, `/markets/trades` | Browse markets, orderbook depth, public trades |
| **Candlesticks** | `/series/{s}/markets/{m}/candlesticks`, `/series/{s}/events/{e}/candlesticks`, `/historical/markets/{m}/candlesticks` | Price history (period_interval: 1=min, 60=hour, 1440=day) |
| **Milestones** | `/milestones`, `/live_data/scores/milestone/{id}`, `/live_data/batch` | Upcoming catalysts, real-time scores/data |
| **Portfolio** | `/portfolio/balance`, `/portfolio/positions`, `/portfolio/settlements`, `/portfolio/summary/total_resting_order_value` | Balance, positions, settlement history |
| **Trading** | `/portfolio/orders`, `/portfolio/orders/batched`, `/portfolio/orders/{id}/amend`, `/portfolio/fills` | Place/cancel/amend orders, trade history |
| **Historical** | `/historical/cutoff`, `/historical/markets`, `/historical/fills`, `/historical/orders`, `/historical/trades` | Archived data (markets >3 months old) |
| **Incentives** | `/incentive_programs` | Rewards programs for trading activity |

**Schemas:** `schema("Market")`, `schema("Event")`, `schema("Series")`, `schema("Order")`, `schema("Fill")`

---

## API Docs Lookup

**Always use `lookup()` and `schema()` to check endpoint details and field names before writing code.** Don't guess field names — the API has many deprecated fields that return 0.

```python
# Look up an endpoint — shows params, request body, response schema
lookup("GET /markets/{ticker}")
lookup("POST /portfolio/orders")
lookup("/events")              # shows all methods for a path

# Look up a schema — shows all fields with types and descriptions
schema("Market")               # the Market object
schema("Order")                # order fields
schema("Event")                # event fields
schema("Series")               # series fields

# Search by keyword
lookup("incentive")            # finds all endpoints matching "incentive"
lookup("candlestick")          # finds candlestick/price history endpoints
lookup("historical")           # finds historical data endpoints
```

---

## How Kalshi Data is Structured

```
Series  →  Events  →  Markets
```

### Series
A recurring template that defines a category of prediction markets. Examples: "NHL Games", "NYC Daily Weather", "Fed Rate Decision". Identified by `series_ticker` (e.g. `KXNHLGAME`, `KXHIGHNY`, `KXFEDDECISION`).

- Use `GET /series` to list all series (add `include_volume=True` for volume data)
- Use `GET /series` with `category` param to filter (e.g. `"Sports"`, `"Economics"`, `"Crypto"`)
- Key fields: `ticker`, `title`, `frequency`, `category`, `tags`, `volume_fp` (with include_volume)
- Series define fee structure, settlement sources, and rules shared by all events within them

### Events
A specific instance within a series. Examples: "Senators vs Canucks, Mar 9", "NYC High Temperature Mar 17", "Fed decision in Mar 2026". Contains one or more markets. Identified by `event_ticker`.

- Use `GET /events` with `with_nested_markets=True` to get events with their markets included
- Filter by `series_ticker` to scope to a series, `status` (open/closed/settled) to filter by state
- Key fields: `event_ticker`, `series_ticker`, `title`, `category`, `close_time`, `markets` (when nested)
- Each event can have multiple markets (e.g. an NBA game event has "Team A wins", "Team B wins", spread/total markets)

### Markets
A single tradeable yes/no contract. Examples: "Will the Senators win?", "Will NYC be above 60°F?", "Will the Fed cut rates by 25bps?". Identified by `ticker`. This is what you trade.

- Use `GET /markets` to browse, filter by `series_ticker`, `event_ticker`, `status`
- Key fields: `ticker`, `event_ticker`, `series_ticker`, `title`, `subtitle`, `status`, `close_time`, `rules_primary` (settlement criteria), `market_type` (binary/scalar), `result` (yes/no/"" if unresolved)
- Price fields: `yes_bid_dollars`, `yes_ask_dollars`, `last_price_dollars` (strings like `"0.56"`)
- Activity fields: `volume_fp`, `volume_24h_fp`, `open_interest_fp`, `liquidity_dollars` (strings)
- Run `schema("Market")` for the complete field list

### Ticker format
`SERIES-EVENTDETAILS-OUTCOME` — e.g. `KXNHLGAME-26MAR09OTTVAN-OTT`
```
Series:  KXNHLGAME
Event:   KXNHLGAME-26MAR09OTTVAN
Market:  KXNHLGAME-26MAR09OTTVAN-OTT
```

### Navigating between them
```python
# Top-down: Series → Events → Markets
series = get("/series", {"include_volume": True})
events = get_all("/events", {"series_ticker": "KXNBAGAME", "status": "open", "with_nested_markets": True})
for event in events:
    for market in event["markets"]:
        print(market["ticker"], market["yes_bid_dollars"])

# Bottom-up: Market → Event → Series
r = get(f"/markets/{ticker}")
market = r["market"]
event_ticker = market["event_ticker"]    # go to parent event
series_ticker = market["series_ticker"]  # go to parent series
```

### Multivariate events (combos/parlays)
Combine legs from multiple events into a single bet. `/events` excludes them by default. Use `mve_filter=exclude` on `/markets` to filter them out, `mve_filter=only` to get only combos. Use `/events/multivariate` or `/multivariate_event_collections` to browse them.

---

## Critical Rules (read before writing any code)

### 1. Always paginate list endpoints

`get()` returns ONE page. Use `get_all()` for `/events`, `/markets`, `/portfolio/positions`, `/portfolio/fills`, etc.

```python
# WRONG — only first page:
r = get("/events", {"status": "open", "with_nested_markets": True})

# RIGHT — all pages:
all_events = get_all("/events", {"status": "open", "with_nested_markets": True})
```

### 2. Single-item responses are wrapped

`get("/markets/TICKER")` returns `{"market": {...}}`, NOT the market directly. Same for events and series.

```python
r = get(f"/markets/{ticker}")
market = r["market"]           # MUST unwrap!

r = get(f"/events/{event_ticker}", {"with_nested_markets": True})
event = r["event"]             # MUST unwrap!
markets = event["markets"]     # nested markets are inside the event

r = get(f"/series/{series_ticker}")
series = r["series"]           # MUST unwrap!
```

### 3. Use current field names, not deprecated ones

The API has deprecated integer fields that **return 0**. Always use the `_dollars` and `_fp` string fields:

| What you want | Use this (current) | NOT this (deprecated, returns 0) |
|---|---|---|
| Bid/ask prices | `yes_bid_dollars`, `yes_ask_dollars` (e.g. `"0.56"`) | ~~`yes_bid`~~, ~~`yes_ask`~~ |
| Last price | `last_price_dollars` | ~~`last_price`~~ |
| Volume | `volume_fp`, `volume_24h_fp` (e.g. `"1234.00"`) | ~~`volume`~~, ~~`volume_24h`~~ |
| Open interest | `open_interest_fp` | ~~`open_interest`~~ |

All `_dollars` and `_fp` fields are **strings**. Convert with `float()` for math. Run `schema("Market")` for the full field list.

### 4. Game-day sports markets are HIDDEN

`/events` and `/markets` **DO NOT return game-day sports markets** unless you filter by `series_ticker`.

```python
nba = get_all("/events", {"series_ticker": "KXNBAGAME", "status": "open", "with_nested_markets": True})
nhl = get_all("/events", {"series_ticker": "KXNHLGAME", "status": "open", "with_nested_markets": True})
```

**Game-day series tickers** (always prefixed with `KX`): `KXNBAGAME`, `KXNHLGAME`, `KXMLBGAME`, `KXNFLGAME`, `KXNCAABGAME`, `KXNCAAFGAME`, `KXWBCGAME`, `KXVALORANTGAME`, `KXCSGOGAME`, `KXLOLGAME`

Championship/futures series (e.g. `KXNBA`, `KXMLB`) are DIFFERENT — they have "who will win the title" markets, not individual game markets.

### 5. Status values differ between queries and responses

- **Query filter** (`status` param): `unopened`, `open`, `paused`, `closed`, `settled`
- **Response field** (`status` in objects): `initialized`, `inactive`, `active`, `closed`, `determined`, `finalized`
- **Common mistake:** `status=active` in a query → 400 error. Use `status=open`.

### 6. Candlesticks: live vs historical, and period_interval is in MINUTES

**`period_interval` is in MINUTES, not seconds.** Only three values are valid: `1` (1 min), `60` (1 hour), `1440` (1 day).

**Live vs historical:** Markets before the historical cutoff date use `/historical/...` endpoints. Recent/active markets use `/series/{s}/markets/{m}/...`. Check the cutoff first:

```python
# Check the historical cutoff date
get("/historical/cutoff")  # returns cutoff timestamps

# Live/recent market candlesticks — use for markets AFTER the historical cutoff
get(f"/series/{series_ticker}/markets/{market_ticker}/candlesticks", {
    "period_interval": 60,  # MINUTES: 1=1min, 60=1hour, 1440=1day
    "start_ts": start_unix,
    "end_ts": end_unix,
})

# Historical/archived market candlesticks — ONLY for markets BEFORE the cutoff
# If you get 404 "not found", the market hasn't been archived yet — use the live endpoint above
get(f"/historical/markets/{ticker}/candlesticks", {
    "period_interval": 1440,  # MINUTES: 1=1min, 60=1hour, 1440=1day
    "start_ts": start_unix, "end_ts": end_unix,
})

# Batch candlesticks — up to 100 markets at once (param is market_tickers, not tickers)
get("/markets/candlesticks", {
    "market_tickers": "TICKER1,TICKER2",  # comma-separated, max 100
    "period_interval": 60,
    "start_ts": start_unix, "end_ts": end_unix,
})
# Returns {"markets": [{"ticker": "...", "candlesticks": [...]}, ...]}
```

**Common mistakes:**
- Using `/historical/markets/{ticker}/candlesticks` for a recent market → 404. Recent/settled markets that haven't been archived yet need the `/series/...` path instead.
- Live candlestick price fields use `_dollars` suffix (e.g. `price.close_dollars`), but historical ones don't (e.g. `price.close`). Always check which format you're getting.

---

## Common Workflows

```python
# Browse all open events with nested markets
events = get_all("/events", {"status": "open", "with_nested_markets": True})

# Get all series (with volume)
get("/series", {"include_volume": True})  # volume is in volume_fp field

# Check portfolio
get("/portfolio/balance")
get_all("/portfolio/positions", {"count_filter": "position"})

# Place order (bots should use place_trade() tool instead!)
post("/portfolio/orders", {
    "ticker": "KXNHLGAME-26MAR09OTTVAN-OTT",
    "side": "yes", "action": "buy", "count": 10,
    "type": "limit", "yes_price": 45,  # cents
})

# Cancel order
delete("/portfolio/orders/ORDER_ID")

# Trade history
get_all("/portfolio/fills")
get_all("/markets/trades", {"ticker": "MARKET_TICKER"})

# Historical data — check cutoff first, then use the right endpoint
cutoff = get("/historical/cutoff")  # markets before this date are in /historical/
get_all("/historical/markets", {"series_ticker": "SOME_SERIES"})
# NOTE: /historical/markets series_ticker filter may return unrelated results — verify tickers
```

For any endpoint not listed here, use `lookup()` to find it.

---

## Trading Safety

**If you are a bot, use `place_trade()` tool to place orders — do NOT call post("/portfolio/orders") directly.**
The `place_trade()` tool automatically tracks trades, manages positions, and handles capital.

**Always confirm with the user before placing, canceling, or modifying any order.**

## Risk Guidelines

- Never bet more than 5% of balance on a single market
- Prefer markets with high open interest and volume (easier to exit)
- Always read `rules_primary` before trading — it defines exactly how the market settles
- Limit orders are safer than market orders in thin markets
- Check `volume_24h_fp` — `"0.00"` means nobody is trading
