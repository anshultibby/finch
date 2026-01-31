# Dome API Implementation Fixes

## Summary

Fixed critical issues in Dome API implementation based on official documentation and errors found in conversation logs.

## Issues Fixed

### 1. Wrong Endpoint for Wallet Positions (404 Error)

**Problem**: Using `/polymarket/wallet/{address}` returned 404 error.

**Root Cause**: This endpoint only returns EOA ↔ Proxy mapping, not positions.

**Fix**: Created `get_positions()` function using correct endpoint:
- Changed from: `/polymarket/wallet/{address}`
- Changed to: `/polymarket/positions/wallet/{address}`

**Files Modified**:
- `backend/modules/tools/servers/dome/polymarket/wallet.py`

**Old Code**:
```python
def get_wallet(wallet_address: str):
    endpoint = f"/polymarket/wallet/{wallet_address}"
    return call_dome_api(endpoint)  # 404 error!
```

**New Code**:
```python
def get_positions(wallet_address: str, limit: int = 100):
    endpoint = f"/polymarket/positions/wallet/{wallet_address}"
    params = {"limit": min(max(1, limit), 100)}
    return call_dome_api(endpoint, params)
```

### 2. Wrong Endpoint and Missing Required Parameter for P&L

**Problem**: 
1. Wrong endpoint path (hyphen instead of slash)
2. Missing required `granularity` parameter

**Fix**: 
- Changed endpoint from `/polymarket/wallet-pnl/{address}` to `/polymarket/wallet/pnl/{address}`
- Added required `granularity` parameter (options: "day", "week", "month", "year", "all")

**Files Modified**:
- `backend/modules/tools/servers/dome/polymarket/wallet.py`

**Old Code**:
```python
def get_wallet_pnl(wallet_address: str, start_time=None, end_time=None):
    endpoint = f"/polymarket/wallet-pnl/{wallet_address}"  # Wrong!
    params = {}  # Missing required param!
```

**New Code**:
```python
def get_wallet_pnl(
    wallet_address: str,
    granularity: Literal["day", "week", "month", "year", "all"] = "day",
    start_time: Optional[int] = None,
    end_time: Optional[int] = None
):
    endpoint = f"/polymarket/wallet/pnl/{wallet_address}"  # Fixed!
    params = {"granularity": granularity}  # Required param!
```

### 3. Missing Wallet Activity Endpoint

**Problem**: No function to get wallet-specific trading activity. The existing `get_trade_history()` returns market-wide trades, not wallet-specific.

**Fix**: Created new `get_wallet_activity()` function using `/polymarket/activity` endpoint.

**Files Modified**:
- `backend/modules/tools/servers/dome/polymarket/wallet.py` (added new function)
- `backend/modules/tools/servers/dome/polymarket/trading.py` (updated docs to clarify)

**New Function**:
```python
def get_wallet_activity(
    wallet_address: str,
    start_time: Optional[int] = None,
    end_time: Optional[int] = None,
    limit: int = 100,
    offset: int = 0
) -> Dict[str, Any]:
    params = {
        "user": wallet_address,
        "limit": min(max(1, limit), 1000),
        "offset": max(0, offset)
    }
    return call_dome_api("/polymarket/activity", params)
```

This returns BUY/SELL/REDEEM actions for building position history.

### 4. Missing Market Search Parameters

**Problem**: `get_markets()` was missing many available parameters for filtering and searching.

**Fix**: Added missing parameters to match API specification:
- `event_slug`: Filter by event
- `token_id`: Filter by specific tokens
- `search`: Search keywords in title/description
- `status`: Filter by 'open' or 'closed'
- `min_volume`: Minimum trading volume filter
- `start_time` / `end_time`: Time range filters
- `pagination_key`: For efficient pagination

**Files Modified**:
- `backend/modules/tools/servers/dome/polymarket/markets.py`

## Response Structure Corrections

### Markets Response

Corrected documentation to match actual API response:
- Markets have `side_a` and `side_b` objects (not `outcomes` array)
- Each side has `id` (token_id) and `label` fields
- Volume fields: `volume_total`, `volume_1_week`, `volume_1_month`, `volume_1_year`
- Pagination uses `pagination_key` not `offset`

### Positions Response

- Position size in two formats: `shares` (raw) and `shares_normalized` (human-readable)
- Label is 'Yes' or 'No' (not 'outcome')
- Includes `market_status`, `redeemable` flags

## Documentation Created

### 1. Comprehensive README

Created `/backend/modules/tools/servers/dome/README.md` with:
- Quick reference table for all functions
- Common issues & fixes section
- Usage examples for key workflows
- Complete response structure documentation
- Migration guide from old implementation
- Testing guidelines

### 2. Updated Main Servers README

Updated `/backend/modules/tools/servers/README.md`:
- Added Dome API to available servers list
- Added prediction markets quick reference section
- Linked to detailed Dome README

## Key Implementation Patterns

### 1. Always Check for Errors

```python
result = get_positions(wallet_address)
if 'error' in result:
    print(f"Error: {result['error']}")
    return
# Safe to access result['positions']
```

### 2. Building Position History

```python
# Get current positions
positions = get_positions(wallet_address)

# Get historical activity
activity = get_wallet_activity(wallet_address, limit=1000)

# Process activity to build history
for act in activity['activities']:
    if act['side'] == 'BUY':
        # Add to position
    elif act['side'] == 'SELL':
        # Reduce position
    elif act['side'] == 'REDEEM':
        # Close position, calculate P&L
```

### 3. Consensus Detection

```python
top_traders = ["0xabc...", "0xdef..."]
market_positions = {}

for trader in top_traders:
    positions = get_positions(trader)
    for pos in positions['positions']:
        key = (pos['market_slug'], pos['label'])
        market_positions[key] = market_positions.get(key, []) + [trader]

# Find consensus (2+ traders)
consensus = {k: v for k, v in market_positions.items() if len(v) >= 2}
```

## Testing

Created test script (`test_dome_urllib.py`) that validates all fixes:
- Tests get_positions() with correct endpoint
- Tests get_wallet_pnl() with required granularity parameter
- Tests get_wallet_activity() for wallet-specific trades
- Tests get_markets() with enhanced search parameters

## Impact

These fixes resolve the 404 errors and missing functionality that prevented:
1. Building Polymarket copy trading strategies
2. Tracking wallet positions over time
3. Analyzing trader performance
4. Detecting consensus signals from multiple traders

All functionality is now working according to official Dome API specification.

## References

- Official Dome API Docs: https://docs.domeapi.io/
- Error logs analyzed: `backend/chat_logs/20260126/152838_3a6a22d2-d0db-498b-8b9d-e98813c043c2/`
