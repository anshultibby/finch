"""
Test Dome API integration

Quick test to verify Dome API is properly integrated into the servers directory.
"""
import sys
sys.path.insert(0, 'modules/tools')

print("Testing Dome API Integration\n" + "="*50)

# Test 1: Import modules
print("\n1. Testing imports...")
try:
    from servers.dome import polymarket, kalshi, matching
    from servers.dome._client import call_dome_api
    print("   ✓ All Dome modules imported successfully")
except Exception as e:
    print(f"   ✗ Import failed: {e}")
    sys.exit(1)

# Test 2: Check API key
print("\n2. Checking API key...")
import os
from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv('DOME_API_KEY')
if api_key:
    print(f"   ✓ API key found: {api_key[:8]}...{api_key[-4:]}")
else:
    print("   ✗ DOME_API_KEY not found in environment")
    sys.exit(1)

# Test 3: Test rate limiter
print("\n3. Testing rate limiter...")
try:
    from servers.dome._client import _rate_limiter
    import time
    
    start = time.time()
    _rate_limiter.wait()
    _rate_limiter.wait()
    elapsed = time.time() - start
    
    # Should take ~1 second (rate limit is 1 req/sec)
    if elapsed >= 0.9:  # Allow some tolerance
        print(f"   ✓ Rate limiter working (waited {elapsed:.2f}s for 2 requests)")
    else:
        print(f"   ⚠ Rate limiter may not be working properly (only waited {elapsed:.2f}s)")
except Exception as e:
    print(f"   ✗ Rate limiter test failed: {e}")

# Test 4: Make a real API call
print("\n4. Testing real API call (searching crypto markets)...")
try:
    result = polymarket.get_markets(tags=['crypto'], limit=3)
    
    if 'error' in result:
        print(f"   ✗ API call failed: {result['error']}")
    else:
        markets = result.get('markets', [])
        print(f"   ✓ API call successful! Found {len(markets)} markets")
        
        if markets:
            print("\n   Sample market:")
            m = markets[0]
            print(f"     Title: {m.get('title', 'N/A')}")
            print(f"     Volume: ${m.get('volume', 0):,.0f}")
            print(f"     Status: {m.get('status', 'N/A')}")
            
except Exception as e:
    print(f"   ✗ API call failed with exception: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*50)
print("Integration test complete!")
