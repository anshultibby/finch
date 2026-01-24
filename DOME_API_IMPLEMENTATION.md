# Dome API Implementation

## Overview

Dome API has been integrated as a file-based tool in the Finch system, accessible via Python code execution. The implementation provides access to Polymarket and Kalshi prediction markets through Dome's unified API.

## Location

```
backend/modules/tools/servers/dome/
├── __init__.py          # Package initialization
├── _client.py           # API client with rate limiting
├── polymarket/          # Polymarket endpoints
│   ├── __init__.py
│   ├── markets.py       # Search and discovery
│   ├── prices.py        # Real-time and historical prices
│   ├── trading.py       # Trade history
│   └── wallet.py        # Wallet positions and P&L
├── kalshi/              # Kalshi endpoints (via Dome)
│   ├── __init__.py
│   └── markets.py       # Markets and pricing
└── matching/            # Cross-platform matching
    ├── __init__.py
    └── sports.py        # Sports arbitrage
```

**File Organization Benefits:**
- **Smaller files** - LLM only reads what it needs
- **Clear organization** - Functions grouped by purpose
- **Better imports** - More specific import paths
- **Easier maintenance** - Changes isolated to specific files

## Rate Limiting

**Critical:** Dome API free tier allows **1 request per second**.

The implementation includes automatic rate limiting:
- Each API call automatically waits to respect the 1 req/sec limit
- Uses a global rate limiter to track requests across all functions
- No manual delay management needed - just call the functions

## Usage Examples

### 1. Search Polymarket Markets

```python
from servers.dome.polymarket.markets import get_markets

# Find crypto-related markets
markets = get_markets(tags=['crypto'], limit=10)
if 'error' not in markets:
    for m in markets['markets']:
        print(f"{m['title']}")
        print(f"  Volume: ${m['volume']:,.0f}")
        print(f"  Token ID (Yes): {m['outcomes'][0]['token_id']}")
```

### 2. Get Market Prices

```python
from servers.dome.polymarket.prices import get_market_price

# Get current price for a specific market outcome
token_id = "98250445447699368679516529207365255018790721464..."
price = get_market_price(token_id)
if 'error' not in price:
    prob = price['price'] * 100
    print(f"Current probability: {prob:.1f}%")

# Get historical price
historical = get_market_price(token_id, at_time=1640995200)
```

### 3. Get Candlestick Data for Charting

```python
from servers.dome.polymarket.prices import get_candlesticks
import pandas as pd
import time

# Get daily candles for last month
end = int(time.time())
start = end - (30 * 24 * 60 * 60)

candles = get_candlesticks(
    condition_id="0x4567b275e6b667a6217f5cb4f06a797d3a1eaf1d0281...",
    start_time=start,
    end_time=end,
    interval=1440  # 1440 = daily, 60 = hourly, 1 = minute
)

if 'error' not in candles:
    # Convert to DataFrame
    data = []
    for candle_array, token_meta in candles['candlesticks']:
        for candle in candle_array:
            data.append({
                'timestamp': pd.to_datetime(candle['end_period_ts'], unit='s'),
                'close': candle['price']['close'],
                'volume': candle['volume'],
                'open_interest': candle['open_interest']
            })
    df = pd.DataFrame(data)
    
    # Create chart
    import plotly.graph_objects as go
    fig = go.Figure(data=[go.Candlestick(
        x=df['timestamp'],
        close=df['close'],
        # ... more config
    )])
```

### 4. Search Kalshi Markets

```python
from servers.dome.kalshi.markets import get_markets

# Get active Federal Reserve rate decision markets
markets = get_markets(series_ticker='FED', status='active', limit=20)
if 'error' not in markets:
    for m in markets['markets']:
        print(f"{m['ticker']}: {m['title']}")
        print(f"  YES: {m['yes_bid']}¢ / {m['yes_ask']}¢")
```

### 5. Track Trade History

```python
from servers.dome.polymarket.trading import get_trade_history

# Get recent trades for a market
trades = get_trade_history(
    condition_id="0x4567b275...",
    limit=50
)
if 'error' not in trades:
    for trade in trades['trades']:
        print(f"{trade['timestamp']}: {trade['side']} "
              f"{trade['size']} shares @ ${trade['price']}")

# Track a specific wallet's trading activity
trades = get_trade_history(
    maker_address="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
    limit=100
)
```

### 6. Monitor Wallet Performance

```python
from servers.dome.polymarket.wallet import get_wallet, get_wallet_pnl

# Get current wallet positions
wallet = get_wallet("0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb")
if 'error' not in wallet:
    print(f"Total portfolio value: ${wallet['total_value']:,.2f}\n")
    for pos in wallet['positions']:
        print(f"{pos['market_slug']}")
        print(f"  Size: {pos['size']} shares")
        print(f"  Entry: ${pos['average_price']:.3f}")
        print(f"  Current: ${pos['current_price']:.3f}")
        print(f"  P&L: ${pos['unrealized_pnl']:,.2f}\n")

# Get P&L history
pnl = get_wallet_pnl("0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb")
if 'error' not in pnl:
    print(f"Total realized P&L: ${pnl['total_pnl']:,.2f}")
    print(f"Win rate: {pnl['win_rate']*100:.1f}%")
    print(f"Total volume: ${pnl['total_volume']:,.0f}")
    print(f"Number of trades: {pnl['num_trades']}")
```

### 7. Find Arbitrage Opportunities

```python
from servers.dome.matching.sports import get_sports_matching_markets, get_sport_by_date

# Find NBA markets on both Polymarket and Kalshi
matches = get_sports_matching_markets(sport='NBA', limit=20)
if 'error' not in matches:
    for match in matches['matches']:
        poly = match.get('polymarket', {})
        kal = match.get('kalshi', {})
        
        if poly and kal:
            poly_prob = poly.get('price', 0)  # 0-1
            kal_prob = kal.get('price', 0) / 100  # cents to 0-1
            
            diff = abs(poly_prob - kal_prob)
            if diff > 0.05:  # 5% difference
                print(f"\n⚠️ Arbitrage opportunity!")
                print(f"Event: {match['event_description']}")
                print(f"Polymarket: {poly_prob*100:.1f}%")
                print(f"Kalshi: {kal_prob*100:.1f}%")
                print(f"Difference: {diff*100:.1f}%")

# Find markets for specific date (e.g., Christmas Day games)
matches = get_sport_by_date(sport='NBA', date='2024-12-25')
if 'error' not in matches:
    print(f"NBA games on {matches['date']}:")
    for match in matches['matches']:
        print(f"  {match['event_description']}")
```

## API Reference

### Polymarket

Import from `servers.dome.polymarket.*` submodules:

#### `get_markets(...)`
Search and discover Polymarket markets.

**Parameters:**
- `market_slug` (List[str], optional): Filter by market slug(s)
- `condition_id` (List[str], optional): Filter by condition ID(s)
- `tags` (List[str], optional): Filter by tags (e.g., ['crypto', 'politics'])
- `limit` (int): Results to return (1-100, default 10)
- `offset` (int): Skip for pagination (default 0)

**Returns:** Dict with `markets` list and `pagination` info

#### `get_market_price(...)`
Get current or historical price for a market outcome.

**Parameters:**
- `token_id` (str): Token ID from market outcomes
- `at_time` (int, optional): Unix timestamp for historical price

**Returns:** Dict with `price` (0-1) and `at_time`

#### `get_candlesticks(...)`
Get OHLC candlestick data for charting.

**Parameters:**
- `condition_id` (str): Market condition ID
- `start_time` (int): Start Unix timestamp
- `end_time` (int): End Unix timestamp
- `interval` (1|60|1440): 1min|1hour|1day

**Important:** Intervals have max range limits:
- `interval=1` (1min): max 1 week
- `interval=60` (1hr): max 1 month
- `interval=1440` (1day): max 1 year

**Returns:** Dict with `candlesticks` array

#### `get_trade_history(...)`
Get historical trade data for markets.

**Parameters:**
- `condition_id` (str, optional): Filter by condition ID
- `market_slug` (str, optional): Filter by market slug
- `token_id` (str, optional): Filter by token ID
- `maker_address` (str, optional): Filter by maker wallet
- `start_time` (int, optional): Start Unix timestamp
- `end_time` (int, optional): End Unix timestamp
- `limit` (int): Results to return (1-1000, default 100)
- `offset` (int): Skip for pagination (default 0)

**Returns:** Dict with `trades` list containing trade details (side, price, size, timestamp, addresses)

#### `get_wallet(...)`
Get wallet positions on Polymarket.

**Parameters:**
- `wallet_address` (str): Ethereum wallet address (0x...)

**Returns:** Dict with `positions` list and `total_value`

#### `get_wallet_pnl(...)`
Get profit and loss history for a wallet.

**Parameters:**
- `wallet_address` (str): Ethereum wallet address (0x...)
- `start_time` (int, optional): Start Unix timestamp
- `end_time` (int, optional): End Unix timestamp

**Returns:** Dict with `total_pnl`, `win_rate`, `total_volume`, `num_trades`, `pnl_history`

### Kalshi

Import from `servers.dome.kalshi.markets`:

#### `get_markets(...)`
Search Kalshi markets via Dome.

**Parameters:**
- `series_ticker` (str, optional): Series ticker (e.g., 'FED')
- `status` ('active'|'settled'|'closed', optional)
- `limit` (int): Results to return (1-100, default 10)
- `offset` (int): Skip for pagination (default 0)

**Returns:** Dict with `markets` list

#### `get_market_price(...)`
Get price for a Kalshi market.

**Parameters:**
- `ticker` (str): Market ticker (e.g., 'FED-24FEB28-T4.75')
- `at_time` (int, optional): Unix timestamp for historical price

**Returns:** Dict with `price` (0-100 cents) and `at_time`

### Matching

Import from `servers.dome.matching.sports`:

#### `get_sports_matching_markets(...)`
Find matching markets across Polymarket and Kalshi.

**Parameters:**
- `sport` (str, optional): Sport filter ('NBA', 'NFL', etc.)
- `limit` (int): Results to return (1-100, default 10)

**Returns:** Dict with `matches` array containing paired markets

#### `get_sport_by_date(...)`
Find matching markets for a specific sport on a specific date.

**Parameters:**
- `sport` (str): Sport name ('NBA', 'NFL', 'MLB', 'NHL')
- `date` (str): Date in YYYY-MM-DD format (e.g., '2024-12-25')

**Returns:** Dict with `sport`, `date`, and `matches` array for games on that date

## Error Handling

All functions return a dict. Check for errors:

```python
result = get_markets(tags=['crypto'])

if 'error' in result:
    print(f"Error: {result['error']}")
else:
    # Process result
    markets = result['markets']
```

Common errors:
- `"DOME_API_KEY not found in environment variables"` - API key not set
- `"HTTP 401: ..."` - Invalid API key
- `"HTTP 429: ..."` - Rate limit exceeded (shouldn't happen with auto-limiting)
- `"Request failed: ..."` - Network/connection issues

## Configuration

The API key is automatically loaded from the environment variable `DOME_API_KEY`.

In production, this is set from the database via the code execution environment setup.

## Design Notes

### Why File-Based Instead of Direct Tools?

1. **Flexibility**: Can be used in complex Python code with loops, conditionals, data processing
2. **Composability**: Easy to combine with pandas, plotting, other APIs
3. **Rate Limiting**: Single global limiter handles all requests properly
4. **Code Reusability**: Analysis code with Dome API calls can be saved and reused
5. **Natural Integration**: Works seamlessly with existing financial data APIs

### Rate Limiting Implementation

- Uses a simple thread-safe rate limiter with global state
- Tracks last request time
- Automatically sleeps between requests to maintain 1 req/sec
- Future-proof: Can easily adjust for higher tiers

### Sync vs Async

The implementation uses synchronous `httpx.Client` (not async) because:
1. Code execution environment uses `asyncio.run()` which requires sync functions
2. Rate limiting with sleep is simpler in sync code
3. 1 req/sec means async provides minimal benefit
4. Avoids event loop complications in subprocess

## Testing

To test manually:

```python
from servers.dome.polymarket import get_markets

# Should return top crypto markets
result = get_markets(tags=['crypto'], limit=5)
print(result)
```

## Future Enhancements

Potential additions:
- Order history endpoints
- Wallet/position tracking
- Orderbook history
- More matching market categories (politics, economics, etc.)
- Caching layer for frequently-accessed data
- Batch request optimization

## References

- Dome API Docs: https://docs.domeapi.io/
- Free Tier Limits: 1 req/sec, 10 req/10sec
