# Dome API Matching Markets Implementation

## Overview

Enhanced the Dome API integration with comprehensive market matching functionality to identify equivalent markets across Polymarket and Kalshi prediction market platforms. This enables cross-platform arbitrage detection and price comparison.

## What Changed

### 1. Updated Matching Markets API (`backend/modules/tools/servers/dome/matching/sports.py`)

**Previous Implementation:**
- Basic sport filtering only
- Generic parameters that didn't match actual API
- Incorrect response structure expectations

**New Implementation:**
- ✅ Query by specific Polymarket market slugs
- ✅ Query by specific Kalshi event tickers  
- ✅ Query by sport and date
- ✅ Correct response structure (markets dict, not matches array)
- ✅ Full type hints with Literal types for sport enums
- ✅ Comprehensive docstrings with examples

### 2. New Arbitrage Detection (`find_arbitrage_opportunities()`)

Added intelligent arbitrage opportunity finder that:
1. Gets all matching markets for a sport/date
2. Fetches real-time prices from both platforms
3. Calculates spreads and identifies profitable opportunities
4. Returns detailed opportunity data with direction (buy poly/sell kalshi or vice versa)

**Parameters:**
- `sport`: Sport abbreviation (nfl, nba, mlb, etc.)
- `date`: Date in YYYY-MM-DD format
- `min_spread`: Minimum price difference to flag (default 5%)

**Returns:**
- Market key and identifiers
- Current prices on both platforms
- Spread percentage
- Recommended arbitrage direction

## API Endpoints Used

### 1. Get Matching Markets by Identifiers
```
GET /matching-markets/sports
Query params: 
  - polymarket_market_slug[] (array)
  - kalshi_event_ticker[] (array)
```

### 2. Get Sport Markets by Date
```
GET /matching-markets/sports/{sport}
Query params:
  - date (YYYY-MM-DD)
```

## Response Structure

Both endpoints return:
```python
{
  "markets": {
    "market-key": [
      {
        "platform": "POLYMARKET",
        "market_slug": "...",
        "token_ids": ["...", "..."]
      },
      {
        "platform": "KALSHI", 
        "event_ticker": "...",
        "market_tickers": ["...", "..."]
      }
    ]
  },
  "sport": "nba",  # Only in sport-by-date endpoint
  "date": "2026-02-01"  # Only in sport-by-date endpoint
}
```

## Usage Examples

### Find All Markets for a Sport/Date
```python
from modules.tools.servers.dome.matching import get_sport_by_date

result = get_sport_by_date(sport='nba', date='2026-02-01')

for market_key, platforms in result['markets'].items():
    has_both = len(platforms) == 2
    if has_both:
        print(f"Cross-platform opportunity: {market_key}")
```

### Find Matches for Specific Markets
```python
from modules.tools.servers.dome.matching import get_sports_matching_markets

# By Polymarket slug
result = get_sports_matching_markets(
    polymarket_market_slug=['nba-lal-gsw-2026-02-01']
)

# By Kalshi ticker
result = get_sports_matching_markets(
    kalshi_event_ticker=['KXNBAGAME-26FEB01LALGSW']
)
```

### Find Arbitrage Opportunities
```python
from modules.tools.servers.dome.matching import find_arbitrage_opportunities
from datetime import datetime, timedelta

tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

result = find_arbitrage_opportunities(
    sport='nba',
    date=tomorrow,
    min_spread=0.03  # 3% minimum
)

for opp in result['opportunities']:
    print(f"{opp['market_key']}")
    print(f"  Spread: {opp['spread']*100:.1f}%")
    print(f"  Strategy: {opp['arbitrage_type']}")
```

## Supported Sports

- `nfl`: Football
- `mlb`: Baseball
- `cfb`: College Football
- `nba`: Basketball
- `nhl`: Hockey
- `cbb`: College Basketball
- `pga`: Golf
- `tennis`: Tennis

## Testing

### Exploration Script
`experiments/explore_dome_matching.py` - Comprehensive exploration of all matching endpoints
- Tests sport/date queries
- Tests slug/ticker queries
- Identifies cross-platform markets
- Demonstrates API response structures

### Unit Tests
- `experiments/test_matching_updated.py` - Tests updated implementation
- `experiments/test_arbitrage_finder.py` - Tests arbitrage detection
- `experiments/demo_dome_matching.py` - Interactive demo

Run tests:
```bash
backend/venv/bin/python experiments/explore_dome_matching.py
backend/venv/bin/python experiments/test_matching_updated.py
backend/venv/bin/python experiments/test_arbitrage_finder.py
backend/venv/bin/python experiments/demo_dome_matching.py
```

## Rate Limiting

The Dome API free tier allows 1 request per second. The implementation includes:
- Built-in rate limiter in `_client.py`
- Automatic throttling between requests
- Graceful handling of rate limit errors

**Note:** The `find_arbitrage_opportunities()` function makes many API calls:
- 1 call to get matching markets
- 2 calls per market (Polymarket + Kalshi prices)
- For 10 markets: ~21 seconds minimum due to rate limiting

## Integration with Existing Code

The matching functionality integrates seamlessly:

```python
# All dome functionality accessible via submodules
from modules.tools.servers.dome import polymarket, kalshi, matching

# Polymarket markets
markets = polymarket.get_markets(tags=['sports'], status='open')

# Kalshi markets  
kalshi_markets = kalshi.get_markets(status='active')

# Find matches
matches = matching.get_sport_by_date(sport='nba', date='2026-02-01')

# Find arbitrage
arb = matching.find_arbitrage_opportunities(sport='nba', date='2026-02-01')
```

## Key Improvements

1. **API Accuracy**: Endpoints and parameters now match official Dome API exactly
2. **Response Handling**: Correctly parses the actual API response structure
3. **Type Safety**: Full type hints with Literal types for enums
4. **Documentation**: Comprehensive docstrings with working examples
5. **Functionality**: New arbitrage detection automates opportunity finding
6. **Testing**: Extensive test scripts validate all functionality

## Files Modified

- `backend/modules/tools/servers/dome/matching/sports.py` - Core implementation
- `backend/modules/tools/servers/dome/matching/__init__.py` - Exports
- `backend/modules/tools/servers/dome/__init__.py` - Module documentation

## Files Created

- `experiments/explore_dome_matching.py` - Comprehensive exploration script
- `experiments/test_matching_updated.py` - Unit tests for matching
- `experiments/test_arbitrage_finder.py` - Arbitrage finder tests
- `experiments/demo_dome_matching.py` - Interactive demo
- `experiments/test_imports.py` - Import verification
- `DOME_MATCHING_IMPLEMENTATION.md` - Complete technical documentation
- `DOME_MATCHING_README.md` - Quick start guide

## Next Steps

Potential enhancements:
1. Add caching to reduce API calls
2. Implement batch price fetching for faster arbitrage detection
3. Add historical arbitrage tracking
4. Create alerts for large spreads
5. Add support for non-sports matching markets (when API supports it)
