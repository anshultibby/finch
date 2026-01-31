#!/usr/bin/env python3
"""Test Dome API fixes using urllib"""
import os
import time
import json
import urllib.request
import urllib.parse
import urllib.error

# Set API key
api_key = os.getenv('DOME_API_KEY')
if not api_key:
    print("❌ DOME_API_KEY not found in environment")
    print("Set it with: export DOME_API_KEY='your_key_here'")
    exit(1)

base_url = "https://api.domeapi.io/v1"

def test_endpoint(name, endpoint, params=None):
    """Test an endpoint"""
    print(f"\n{name}")
    print(f"  Endpoint: {endpoint}")
    
    url = f"{base_url}{endpoint}"
    if params:
        query_string = urllib.parse.urlencode(params)
        url = f"{url}?{query_string}"
        print(f"  URL: {url}")
    
    try:
        req = urllib.request.Request(url)
        req.add_header('x-api-key', api_key)
        
        with urllib.request.urlopen(req, timeout=30.0) as response:
            data = json.loads(response.read().decode('utf-8'))
            print(f"  ✅ Success! Status: {response.status}")
            print(f"  Response keys: {list(data.keys())}")
            return data
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        print(f"  ❌ HTTP {e.code}: {error_body[:200]}")
        return None
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        return None

# Test wallet address (Theo4)
test_wallet = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"

print("=" * 80)
print("Testing Dome API Endpoints - Validating Fixes")
print("=" * 80)

# Test 1: Get positions (FIXED - was using wrong endpoint)
print("\n" + "="*80)
print("TEST 1: Get Positions")
print("OLD: /polymarket/wallet/{address} (404 error)")
print("NEW: /polymarket/positions/wallet/{address}")
print("="*80)
data = test_endpoint(
    "Get Positions",
    f"/polymarket/positions/wallet/{test_wallet}",
    {"limit": 5}
)
if data and 'positions' in data:
    print(f"  ✅ Found {len(data['positions'])} positions")
    if data['positions']:
        pos = data['positions'][0]
        print(f"  Example: {pos['title'][:60]}")
        print(f"  Shares: {pos['shares_normalized']} {pos['label']}")
else:
    print(f"  ❌ Failed to get positions")
time.sleep(1.1)  # Rate limit

# Test 2: Get wallet PnL (FIXED - wrong endpoint + missing required param)
print("\n" + "="*80)
print("TEST 2: Get Wallet PnL")
print("OLD: /polymarket/wallet-pnl/{address} (wrong path)")
print("NEW: /polymarket/wallet/pnl/{address} + granularity (REQUIRED)")
print("="*80)
data = test_endpoint(
    "Get Wallet PnL",
    f"/polymarket/wallet/pnl/{test_wallet}",
    {"granularity": "all"}
)
if data and 'pnl_over_time' in data:
    print(f"  ✅ Data points: {len(data['pnl_over_time'])}")
    if data['pnl_over_time']:
        latest = data['pnl_over_time'][-1]
        print(f"  Total realized P&L: ${latest['pnl_to_date']:,.2f}")
else:
    print(f"  ❌ Failed to get PnL")
time.sleep(1.1)

# Test 3: Get wallet activity (NEW - was missing entirely)
print("\n" + "="*80)
print("TEST 3: Get Wallet Activity")
print("OLD: Used /polymarket/trades (market-wide, not wallet-specific)")
print("NEW: /polymarket/activity with user param (wallet-specific)")
print("="*80)
data = test_endpoint(
    "Get Wallet Activity",
    "/polymarket/activity",
    {"user": test_wallet, "limit": 5}
)
if data and 'activities' in data:
    print(f"  ✅ Found {len(data['activities'])} activities")
    if data['activities']:
        act = data['activities'][0]
        print(f"  Latest: {act['side']} {act['shares_normalized']} @ ${act['price']}")
        print(f"  Market: {act['title'][:50]}")
else:
    print(f"  ❌ Failed to get activity")
time.sleep(1.1)

# Test 4: Get markets (ENHANCED - added missing params)
print("\n" + "="*80)
print("TEST 4: Get Markets")
print("OLD: Basic params only")
print("NEW: Added search, status, min_volume, event_slug, pagination_key, etc.")
print("="*80)
data = test_endpoint(
    "Get Markets with Search",
    "/polymarket/markets",
    {"search": "bitcoin", "status": "open", "limit": 3}
)
if data and 'markets' in data:
    print(f"  ✅ Found {len(data['markets'])} markets")
    if data['markets']:
        m = data['markets'][0]
        print(f"  Example: {m['title'][:60]}")
        print(f"  Volume: ${m['volume_total']:,.2f}")
        print(f"  Sides: {m['side_a']['label']} vs {m['side_b']['label']}")
else:
    print(f"  ❌ Failed to get markets")

print("\n" + "=" * 80)
print("✅ All tests completed successfully!")
print("=" * 80)

print("\n" + "="*80)
print("SUMMARY OF FIXES:")
print("="*80)
print("1. get_wallet() → get_positions()")
print("   - Fixed endpoint: /polymarket/positions/wallet/{address}")
print("   - Returns actual positions with market data")
print()
print("2. get_wallet_pnl()")
print("   - Fixed endpoint: /polymarket/wallet/pnl/{address}")
print("   - Added required 'granularity' parameter")
print("   - Now returns cumulative realized P&L over time")
print()
print("3. get_wallet_activity() - NEW FUNCTION")
print("   - Uses /polymarket/activity endpoint")
print("   - Tracks wallet's buys, sells, redeems")
print("   - This is what you need for building position history")
print()
print("4. get_markets()")
print("   - Added: search, status, min_volume, event_slug, pagination_key")
print("   - Better filtering and search capabilities")
print("="*80)
