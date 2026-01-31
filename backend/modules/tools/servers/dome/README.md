# Dome API - Prediction Market Data Access

Dome API provides unified access to Polymarket and Kalshi prediction market data with enhanced analytics and historical data not available through native APIs.

**Base URL**: `https://api.domeapi.io/v1`  
**Rate Limit**: 1 request/second (free tier), automatically enforced by client

## Quick Reference

| Task | Function | Module |
|------|----------|--------|
| Get wallet positions | `get_positions(address)` | `wallet.py` |
| Get wallet P&L | `get_wallet_pnl(address, granularity)` | `wallet.py` |
| Get wallet activity | `get_wallet_activity(address)` | `wallet.py` |
| Get wallet info | `get_wallet_info(eoa/proxy)` | `wallet.py` |
| Search markets | `get_markets(...)` | `markets.py` |
| Get market price | `get_market_price(token_id)` | `prices.py` |
| Get candlesticks | `get_candlesticks(condition_id, ...)` | `prices.py` |
| Get trade history | `get_trade_history(...)` | `trading.py` |

## Common Issues & Fixes

### Issue 1: "HTTP 404: route not found" when getting wallet data

**Problem**: Using wrong endpoint for positions.

```python
# ❌ WRONG - This only returns EOA/proxy mapping
from servers.dome.polymarket.wallet import get_wallet
result = get_wallet(address)  # 404 error!

# ✅ CORRECT - Use get_positions for actual positions
from servers.dome.polymarket.wallet import get_positions
result = get_positions(address)
```

**Explanation**: The `/polymarket/wallet` endpoint only returns EOA ↔ Proxy address mapping. Use `/polymarket/positions/wallet/{address}` to get actual positions.

### Issue 2: Missing 'granularity' parameter for P&L

**Problem**: `get_wallet_pnl()` requires `granularity` parameter.

```python
# ❌ WRONG - Missing required parameter
from servers.dome.polymarket.wallet import get_wallet_pnl
result = get_wallet_pnl(address)  # Error!

# ✅ CORRECT - Provide granularity
result = get_wallet_pnl(address, granularity="day")
# Options: "day", "week", "month", "year", "all"
```

**Note**: P&L endpoint returns REALIZED P&L only (from sells/redeems), not unrealized. Different from Polymarket dashboard.

### Issue 3: Getting wallet-specific trades

**Problem**: Using wrong endpoint for wallet activity.

```python
# ❌ WRONG - This returns market-wide trades
from servers.dome.polymarket.trading import get_trade_history
trades = get_trade_history(maker_address=wallet)  # Not wallet-specific!

# ✅ CORRECT - Use activity endpoint
from servers.dome.polymarket.wallet import get_wallet_activity
activity = get_wallet_activity(wallet, limit=100)
# Returns BUY/SELL/REDEEM actions for this wallet
```

**Explanation**: `/polymarket/trades` returns all platform trades. Use `/polymarket/activity` with `user` param for wallet-specific trades.

## Module Organization

```
dome/
├── README.md                    # This file
├── _client.py                   # HTTP client with rate limiting
├── polymarket/
│   ├── wallet.py                # Wallet positions, P&L, activity
│   ├── markets.py               # Market search and discovery
│   ├── prices.py                # Current prices and candlesticks
│   └── trading.py               # Market-wide trade history
├── kalshi/
│   └── markets.py               # Kalshi market data
└── matching/
    └── sports.py                # Cross-platform market matching
```

## Key Concepts

### 1. Wallet Addresses

Polymarket uses two address types:
- **EOA** (Externally Owned Account): User's actual wallet
- **Proxy**: Smart contract wallet used for trading

Use `get_wallet_info(eoa=...)` to map between them. Most endpoints require the **proxy** address.

### 2. Market Identifiers

Markets have multiple identifiers:
- **market_slug**: Human-readable (e.g., `"bitcoin-up-or-down-july-25"`)
- **condition_id**: Unique condition hash (e.g., `"0x4567b275..."`)
- **token_id**: Specific outcome token (each market has 2: Yes and No)

Use the appropriate identifier based on the endpoint.

### 3. Position Tracking

To track wallet positions over time:

1. **Current positions**: Use `get_positions(address)`
2. **Historical activity**: Use `get_wallet_activity(address)`
3. **Realized P&L**: Use `get_wallet_pnl(address, granularity="day")`

Build position history by processing activity:
- `BUY` actions increase position
- `SELL` actions decrease position
- `REDEEM` actions close position and realize P&L

## Usage Examples

### Track Top Trader Positions

```python
from servers.dome.polymarket.wallet import get_positions, get_wallet_activity

# Top trader address
trader = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"

# Get current positions
positions = get_positions(trader, limit=100)
if 'error' not in positions:
    for pos in positions['positions']:
        print(f"{pos['title']}: {pos['shares_normalized']} {pos['label']}")

# Get recent activity
activity = get_wallet_activity(trader, limit=50)
if 'error' not in activity:
    for act in activity['activities']:
        print(f"{act['side']}: {act['shares_normalized']} @ ${act['price']}")
```

### Search for Markets

```python
from servers.dome.polymarket.markets import get_markets

# Search by keyword
markets = get_markets(search="bitcoin", status="open", limit=20)
if 'error' not in markets:
    for m in markets['markets']:
        print(f"{m['title']}")
        print(f"  Volume: ${m['volume_total']:,.0f}")
        print(f"  {m['side_a']['label']} (token: {m['side_a']['id']})")
        print(f"  {m['side_b']['label']} (token: {m['side_b']['id']})")

# Filter by tags and volume
markets = get_markets(
    tags=['crypto'],
    min_volume=10000,
    status='open'
)
```

### Get Market Price History

```python
from servers.dome.polymarket.prices import get_candlesticks
import time

# Get daily candles for last 30 days
end = int(time.time())
start = end - (30 * 24 * 60 * 60)

candles = get_candlesticks(
    condition_id="0x4567b275...",
    start_time=start,
    end_time=end,
    interval=1440  # Daily candles
)

if 'error' not in candles:
    for candle_array, token_meta in candles['candlesticks']:
        for candle in candle_array:
            print(f"Close: {candle['price']['close']}")
            print(f"Volume: {candle['volume']}")
```

### Build Consensus Signal

```python
from servers.dome.polymarket.wallet import get_positions

top_traders = [
    "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",  # Theo4
    "0x9d0e71d7d57e0f6b354d8f5e3c7c8e2f3d6a1b2c",  # Fredi9999
]

# Find markets where 2+ traders have positions
market_counts = {}
for trader in top_traders:
    positions = get_positions(trader)
    if 'error' not in positions:
        for pos in positions['positions']:
            key = (pos['market_slug'], pos['label'])
            market_counts[key] = market_counts.get(key, 0) + 1

# Filter for consensus (2+ traders)
consensus = {k: v for k, v in market_counts.items() if v >= 2}
for (market, side), count in consensus.items():
    print(f"{market} - {side}: {count} traders")
```

## Error Handling

Always check for errors before accessing data:

```python
result = get_positions(wallet_address)

# Check for errors
if 'error' in result:
    print(f"API Error: {result['error']}")
    # Handle error appropriately
    return

# Safe to access data
for pos in result['positions']:
    process_position(pos)
```

Common error codes:
- `404 Not Found`: Wrong endpoint path
- `400 Bad Request`: Missing required parameter or invalid value
- `429 Too Many Requests`: Rate limit exceeded (should be prevented by client)
- `500 Internal Server Error`: Dome API issue

## Rate Limiting

The client automatically enforces 1 req/sec rate limit:

```python
# Rate limiter in _client.py handles this automatically
from servers.dome.polymarket.wallet import get_positions, get_wallet_activity

# These calls are automatically rate-limited
positions = get_positions(wallet1)  # Executes immediately
activity = get_wallet_activity(wallet1)  # Waits ~1 second
positions2 = get_positions(wallet2)  # Waits another ~1 second
```

No manual rate limiting needed - the client handles it.

## Testing

Use known wallet addresses for testing:

```python
# Top Polymarket traders
TEST_WALLETS = {
    "Theo4": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
    "Fredi9999": "0x9d0e71d7d57e0f6b354d8f5e3c7c8e2f3d6a1b2c",
}

# Test with active trader
test_wallet = TEST_WALLETS["Theo4"]
positions = get_positions(test_wallet)
assert 'error' not in positions
assert 'positions' in positions
```

## Response Structures

### Positions Response

```python
{
    "wallet_address": "0x742d35...",
    "positions": [
        {
            "wallet": "0x742d35...",
            "token_id": "19701256...",
            "condition_id": "0xabcd1234...",
            "title": "Will Bitcoin reach $100k?",
            "shares": 50000000,
            "shares_normalized": 50.0,
            "redeemable": False,
            "market_slug": "bitcoin-100k",
            "label": "Yes",
            "market_status": "open"
        }
    ],
    "pagination": {
        "has_more": False,
        "limit": 100
    }
}
```

### Activity Response

```python
{
    "activities": [
        {
            "token_id": "19701256...",
            "side": "BUY",  # or "SELL", "REDEEM"
            "market_slug": "bitcoin-100k",
            "condition_id": "0xabcd1234...",
            "shares": 50000000,
            "shares_normalized": 50.0,
            "price": 0.65,
            "tx_hash": "0x028baff2...",
            "title": "Will Bitcoin reach $100k?",
            "timestamp": 1721263049,
            "user": "0x742d35..."
        }
    ],
    "pagination": {
        "limit": 100,
        "offset": 0,
        "count": 1250,
        "has_more": True
    }
}
```

### Markets Response

```python
{
    "markets": [
        {
            "market_slug": "bitcoin-100k",
            "event_slug": "bitcoin-predictions",
            "condition_id": "0xabcd1234...",
            "title": "Will Bitcoin reach $100k?",
            "description": "Market resolves Yes if...",
            "tags": ["crypto", "bitcoin"],
            "volume_total": 125000.50,
            "status": "open",
            "side_a": {
                "id": "19701256...",  # token_id
                "label": "Yes"
            },
            "side_b": {
                "id": "57567439...",  # token_id
                "label": "No"
            },
            "winning_side": None  # or "side_a"/"side_b" if resolved
        }
    ],
    "pagination": {
        "limit": 20,
        "total": 150,
        "has_more": True,
        "pagination_key": "eyJ2b2x1bWU..."
    }
}
```

## Migration from Old Implementation

If you have code using the old incorrect endpoints:

```python
# OLD CODE (with errors)
from servers.dome.polymarket.wallet import get_wallet, get_wallet_pnl
wallet_data = get_wallet(address)  # ❌ 404 error
pnl_data = get_wallet_pnl(address)  # ❌ Missing granularity

# NEW CODE (correct)
from servers.dome.polymarket.wallet import get_positions, get_wallet_pnl
positions = get_positions(address)  # ✅ Works
pnl_data = get_wallet_pnl(address, granularity="day")  # ✅ Works
```

For tracking trades:
```python
# OLD CODE
from servers.dome.polymarket.trading import get_trade_history
trades = get_trade_history(maker_address=wallet)  # ❌ Returns all trades

# NEW CODE
from servers.dome.polymarket.wallet import get_wallet_activity
activity = get_wallet_activity(wallet)  # ✅ Returns wallet-specific
```

## Additional Resources

- Official docs: https://docs.domeapi.io/
- API dashboard: https://dashboard.domeapi.io/
- Discord support: https://discord.gg/fKAbjNAbkt
