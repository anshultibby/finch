---
name: odds_api
description: Live and historical sports odds, scores, and events from The Odds API. Covers NFL, NBA, NHL, MLB, soccer, tennis, MMA, and 70+ sports with odds from 40+ bookmakers. Historical snapshots from June 2020.
homepage: https://the-odds-api.com
metadata:
  emoji: "🏈"
  category: sports_betting
  is_system: true
  requires:
    env:
      - ODDS_API_KEY
    bins: []
---

# The Odds API Skill

Live and upcoming sports odds from 40+ bookmakers across 70+ sports.

## Import Pattern

```python
from skills.odds_api.scripts.odds import (
    get_sports, get_odds, get_event_odds,
    get_scores, get_events, get_event_markets,
    get_participants, get_quota,
    # Historical data (paid plans only)
    get_historical_odds, get_historical_events, get_historical_event_odds,
)
from skills.odds_api.scripts.api_docs import lookup, schema
```

## List Available Sports

```python
from skills.odds_api.scripts.odds import get_sports

# In-season sports only (free, no quota cost)
sports = get_sports()
for s in sports:
    print(f"{s['key']:40s} {s['title']}")

# Include out-of-season sports
all_sports = get_sports(all_sports=True)
```

Common sport keys:
| Sport | Key |
|---|---|
| NFL | `americanfootball_nfl` |
| NBA | `basketball_nba` |
| NHL | `icehockey_nhl` |
| MLB | `baseball_mlb` |
| NCAA Basketball | `basketball_ncaab` |
| NCAA Football | `americanfootball_ncaaf` |
| EPL | `soccer_epl` |
| MLS | `soccer_usa_mls` |
| UFC/MMA | `mma_mixed_martial_arts` |
| Tennis | `tennis_atp_french_open` (varies by tournament) |

## Get Odds

```python
from skills.odds_api.scripts.odds import get_odds

# NBA moneyline odds from US bookmakers (1 credit)
games = get_odds("basketball_nba", regions="us", markets="h2h")
for game in games:
    print(f"{game['away_team']} @ {game['home_team']} — {game['commence_time']}")
    for bk in game.get("bookmakers", []):
        for market in bk["markets"]:
            if market["key"] == "h2h":
                for outcome in market["outcomes"]:
                    print(f"  {bk['title']}: {outcome['name']} {outcome['price']}")

# Spreads + totals from multiple regions (costs more credits)
games = get_odds("americanfootball_nfl", regions="us,us2", markets="h2h,spreads,totals")

# Filter by time window
games = get_odds(
    "basketball_nba",
    commence_time_from="2026-03-17T00:00:00Z",
    commence_time_to="2026-03-18T00:00:00Z",
)

# Specific bookmakers only
games = get_odds("icehockey_nhl", bookmakers="draftkings,fanduel,betmgm")

# Decimal odds (European format)
games = get_odds("soccer_epl", odds_format="decimal", regions="uk")
```

## Get Scores

```python
from skills.odds_api.scripts.odds import get_scores

# Live/upcoming scores (1 credit)
scores = get_scores("basketball_nba")
for game in scores:
    if game.get("completed"):
        print(f"FINAL: {game['away_team']} {game['scores'][0]['score']} - {game['home_team']} {game['scores'][1]['score']}")
    elif game.get("scores"):
        print(f"LIVE: {game['away_team']} vs {game['home_team']}")

# Include completed games from past 3 days (2 credits)
scores = get_scores("icehockey_nhl", days_from=3)
```

## Get Events (Free)

```python
from skills.odds_api.scripts.odds import get_events

# List upcoming events — no odds, no quota cost
events = get_events("baseball_mlb")
for e in events:
    print(f"{e['id']}: {e['away_team']} @ {e['home_team']} — {e['commence_time']}")

# Filter by date range
events = get_events(
    "basketball_nba",
    commence_time_from="2026-03-17T00:00:00Z",
    commence_time_to="2026-03-20T00:00:00Z",
)
```

## Single Event Deep Dive

```python
from skills.odds_api.scripts.odds import get_event_odds, get_event_markets

# See all available markets for an event
markets = get_event_markets("basketball_nba", event_id="abc123")

# Get detailed odds for a single event (all markets)
event = get_event_odds(
    "basketball_nba",
    event_id="abc123",
    markets="h2h,spreads,totals,player_pass_tds",  # include prop markets
)
```

## Quota Management

Each request costs credits (shown in response headers). Track usage:

```python
from skills.odds_api.scripts.odds import get_quota

# After any API call, check remaining quota
quota = get_quota()
print(f"Remaining: {quota['remaining']}, Used: {quota['used']}")
```

**Cost reference:**
- `/sports` and `/events` — Free
- `/odds` — 1 credit per region × market combo
- `/scores` — 1 credit (2 if `days_from` is set)
- `/events/{id}/odds` — 1 credit × unique markets × regions
- `/events/{id}/markets` — 1 credit

## Response Format

Games/events always include:
- `id` — unique event ID
- `sport_key`, `sport_title`
- `home_team`, `away_team`
- `commence_time` — ISO 8601 timestamp

Odds responses add `bookmakers[]`, each with:
- `key`, `title` — bookmaker identifier and display name
- `last_update` — when odds were last refreshed
- `markets[]` — each with `key` (h2h/spreads/totals) and `outcomes[]`
  - Outcome: `name`, `price` (odds value), optional `point` (spread/total line)

## Common Workflows

### Compare Odds Across Bookmakers

```python
games = get_odds("basketball_nba", regions="us", markets="h2h")
for game in games:
    print(f"\n{game['away_team']} @ {game['home_team']}")
    best = {}
    for bk in game["bookmakers"]:
        for market in bk["markets"]:
            for outcome in market["outcomes"]:
                team = outcome["name"]
                price = outcome["price"]
                if team not in best or price > best[team][1]:
                    best[team] = (bk["title"], price)
    for team, (book, price) in best.items():
        print(f"  Best {team}: {price:+d} ({book})")
```

### Find Value Bets (Odds Discrepancies)

```python
games = get_odds("icehockey_nhl", regions="us,us2", markets="h2h")
for game in games:
    prices = {}
    for bk in game["bookmakers"]:
        for m in bk["markets"]:
            for o in m["outcomes"]:
                prices.setdefault(o["name"], []).append(o["price"])
    for team, vals in prices.items():
        spread = max(vals) - min(vals)
        if spread > 30:  # significant odds discrepancy
            print(f"VALUE? {game['home_team']} vs {game['away_team']}: {team} spread={spread}")
```

### Today's Games With Scores

```python
events = get_events("basketball_nba")  # free
scores = get_scores("basketball_nba")  # 1 credit
score_map = {s["id"]: s for s in scores}
for e in events:
    s = score_map.get(e["id"], {})
    status = "FINAL" if s.get("completed") else "LIVE" if s.get("scores") else "UPCOMING"
    print(f"[{status}] {e['away_team']} @ {e['home_team']}")
```

## API Docs Lookup

**Use `lookup()` and `schema()` to check endpoint details before writing code.** These query the live Swagger spec.

```python
from skills.odds_api.scripts.api_docs import lookup, schema

# Look up an endpoint — shows params, response schema
lookup("GET /v4/sports/{sport}/odds")
lookup("/v4/historical/sports/{sport}/odds")  # all methods for a path

# Search by keyword
lookup("historical")     # finds all historical endpoints
lookup("participants")   # finds participant endpoints

# Look up response schemas
schema("OddsResponse")

# List all endpoints or schemas
from skills.odds_api.scripts.api_docs import list_endpoints, list_schemas
list_endpoints()
list_schemas()
```

---

## Historical Data (Paid Plans Only)

Historical odds snapshots are available from **June 6, 2020**. Snapshots at 10-minute intervals (5-minute from September 2022).

### Get Historical Events

Find what events existed at a past timestamp. Use this to get event IDs for historical odds lookups.

```python
from skills.odds_api.scripts.odds import get_historical_events

# What NBA games were listed on Jan 15, 2024?
result = get_historical_events(
    "basketball_nba",
    date="2024-01-15T18:00:00Z",
)
# result has: timestamp, previous_timestamp, next_timestamp, data (list of events)
for event in result["data"]:
    print(f"{event['id']}: {event['away_team']} @ {event['home_team']} — {event['commence_time']}")

# Filter by game time window
result = get_historical_events(
    "americanfootball_nfl",
    date="2024-01-14T12:00:00Z",
    commence_time_from="2024-01-14T00:00:00Z",
    commence_time_to="2024-01-15T00:00:00Z",
)
```

**Cost:** 1 credit (free if no events found).

### Get Historical Odds (All Events)

Snapshot of odds across all events for a sport at a past timestamp.

```python
from skills.odds_api.scripts.odds import get_historical_odds

# NFL odds on a specific date
result = get_historical_odds(
    "americanfootball_nfl",
    date="2024-01-14T18:00:00Z",
    regions="us",
    markets="h2h,spreads,totals",
)
print(f"Snapshot at: {result['timestamp']}")
print(f"Next snapshot: {result['next_timestamp']}")
for event in result["data"]:
    print(f"\n{event['away_team']} @ {event['home_team']}")
    for bk in event.get("bookmakers", []):
        for market in bk["markets"]:
            for outcome in market["outcomes"]:
                print(f"  {bk['title']}: {outcome['name']} {outcome['price']}")

# Navigate between snapshots using previous/next timestamps
next_snap = get_historical_odds(
    "americanfootball_nfl",
    date=result["next_timestamp"],
    regions="us",
    markets="h2h",
)
```

**Cost:** 10 credits per region × market combo (e.g. 3 markets × 1 region = 30 credits).

### Get Historical Event Odds (Single Event)

Odds for a specific event at a past timestamp. Supports any available market including player props (after May 2023).

```python
from skills.odds_api.scripts.odds import get_historical_event_odds

# Get odds for a specific game at a specific time
result = get_historical_event_odds(
    "basketball_nba",
    event_id="abc123def456",  # from get_historical_events()
    date="2024-01-15T19:00:00Z",
    markets="h2h,spreads,totals,player_points",
)
```

**Cost:** 1 credit per request.

### Historical Data Workflow

```python
from skills.odds_api.scripts.odds import (
    get_historical_events, get_historical_odds, get_historical_event_odds,
)

# Step 1: Find events on a date
events = get_historical_events("basketball_nba", date="2024-03-01T12:00:00Z")

# Step 2: Get bulk odds snapshot
odds = get_historical_odds(
    "basketball_nba",
    date="2024-03-01T18:00:00Z",
    regions="us",
    markets="h2h,spreads",
)

# Step 3: Deep dive into a specific game
event_id = events["data"][0]["id"]
detail = get_historical_event_odds(
    "basketball_nba",
    event_id=event_id,
    date="2024-03-01T18:00:00Z",
    markets="h2h,spreads,totals,player_points",
)

# Step 4: Track line movement — walk through snapshots
timestamps = ["2024-03-01T12:00:00Z", "2024-03-01T15:00:00Z", "2024-03-01T18:00:00Z"]
for ts in timestamps:
    snap = get_historical_event_odds(
        "basketball_nba", event_id=event_id, date=ts, markets="spreads",
    )
    print(f"{snap['timestamp']}: {snap['data']}")
```

### Historical Cost Reference

| Endpoint | Cost |
|---|---|
| `get_historical_events()` | 1 credit (free if empty) |
| `get_historical_odds()` | 10 × regions × markets |
| `get_historical_event_odds()` | 1 credit |

---

## Error Handling

```python
result = get_odds("invalid_sport")
if isinstance(result, dict) and "error" in result:
    print(result["error"])  # API key missing, rate limited, etc.
```

## Comparing Vegas Odds to Kalshi Prediction Markets

When combining with the Kalshi skill to find value bets, use **decimal odds** (`odds_format="decimal"`) for easier probability math:

```python
from skills.odds_api.scripts.odds import get_odds
from skills.kalshi_trading.scripts.kalshi import get_all

# Vegas odds in decimal format (implied_prob = 1/decimal_odds)
vegas = get_odds("basketball_nba", regions="us", markets="h2h", odds_format="decimal")

# Kalshi markets (MUST include with_nested_markets=True!)
kalshi = get_all("/events", {
    "series_ticker": "KXNBAGAME", "status": "open", "with_nested_markets": True,
})
# Or: get_all("/markets", {"series_ticker": "KXNBAGAME", "status": "open"})
```

**Key differences between the two APIs:**
| | Odds API | Kalshi |
|---|---|---|
| Team names | Full: `"Houston Rockets"` | Abbreviated in title: `"Los Angeles L at Houston"`, 3-letter in ticker: `HOU` |
| Price format | American (`-150`) or decimal (`1.67`) | Probability as string: `"0.60"` (= 60%) |
| To probability | Decimal: `1/price`. American: `100/(price+100)` if +, `abs(p)/(abs(p)+100)` if - | `float(yes_bid_dollars)` directly |

See the Kalshi SKILL.md "Kalshi vs Vegas Odds Comparison" section for the full workflow.

---

## When to Use This Skill

- User asks about odds for an upcoming game
- User wants to compare lines across bookmakers
- User needs live scores or game schedules
- User wants to find value bets or odds discrepancies
- User wants historical odds data for backtesting or line movement analysis
- Bot needs sports odds data for prediction market decisions (combine with Kalshi skill)
