# Dome Matching Markets - Quick Start

## What It Does

Find equivalent prediction markets across Polymarket and Kalshi to identify arbitrage opportunities and compare prices.

## Quick Start

```python
from modules.tools.servers.dome import matching
from datetime import datetime, timedelta

# Find all NBA markets for tomorrow
tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
result = matching.get_sport_by_date(sport='nba', date=tomorrow)

# Find arbitrage opportunities
arb = matching.find_arbitrage_opportunities(
    sport='nba',
    date=tomorrow,
    min_spread=0.03  # 3% minimum
)
```

## Functions

### `get_sport_by_date(sport, date)`
Get all matching markets for a sport on a specific date.

**Sports:** `'nba'`, `'nfl'`, `'mlb'`, `'nhl'`, `'cfb'`, `'cbb'`, `'pga'`, `'tennis'`

**Returns:** Dict with `markets` mapping market keys to platform data

### `get_sports_matching_markets(polymarket_market_slug=None, kalshi_event_ticker=None)`
Find matches for specific market identifiers.

**Parameters:**
- `polymarket_market_slug`: List of Polymarket slugs
- `kalshi_event_ticker`: List of Kalshi tickers

### `find_arbitrage_opportunities(sport, date, min_spread=0.05)`
Automatically find arbitrage opportunities by comparing prices.

**Returns:** List of opportunities with spread, prices, and trading direction

## Demo

```bash
# Run comprehensive demo
backend/venv/bin/python experiments/demo_dome_matching.py

# Run exploration script
backend/venv/bin/python experiments/explore_dome_matching.py
```

## Files

- `backend/modules/tools/servers/dome/matching/sports.py` - Implementation
- `DOME_MATCHING_IMPLEMENTATION.md` - Full documentation
- `experiments/demo_dome_matching.py` - Interactive demo
- `experiments/explore_dome_matching.py` - API exploration
- `experiments/test_*.py` - Various tests

## Rate Limits

Free tier: 1 request/second (built-in rate limiting)

⚠️ `find_arbitrage_opportunities()` is slow due to rate limits (fetches prices for each market)
