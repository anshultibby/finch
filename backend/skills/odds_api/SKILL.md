---
name: odds_api
description: Live sports odds, scores, and events from The Odds API. Covers NFL, NBA, NHL, MLB, soccer, tennis, MMA, and 70+ sports with odds from 40+ bookmakers.
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
)
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

## Error Handling

```python
result = get_odds("invalid_sport")
if isinstance(result, dict) and "error" in result:
    print(result["error"])  # API key missing, rate limited, etc.
```

## When to Use This Skill

- User asks about odds for an upcoming game
- User wants to compare lines across bookmakers
- User needs live scores or game schedules
- User wants to find value bets or odds discrepancies
- Bot needs sports odds data for prediction market decisions (combine with Kalshi skill)
