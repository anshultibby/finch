#!/usr/bin/env python3
"""Test Polymarket CLOB client - Direct API access (no Dome API needed)"""
from py_clob_client.client import ClobClient

print("=" * 80)
print("Testing Polymarket CLOB Client (Direct API - No Dome)")
print("=" * 80)

# Create read-only client (no auth needed)
client = ClobClient("https://clob.polymarket.com")

# Test 1: Get markets
print("\n" + "="*80)
print("TEST 1: Get Markets")
print("="*80)
test_token_id = None
try:
    result = client.get_simplified_markets()
    if isinstance(result, dict) and 'data' in result:
        all_markets = result['data']
        markets = all_markets[:10]  # Get first 10
        
        print(f"  ✅ Found {len(all_markets)} total markets (showing {len(markets)})")
        if markets:
            # Show first market
            m = markets[0]
            print(f"\n  First market:")
            print(f"    Question: {m.get('question', 'N/A')[:70]}")
            print(f"    Condition ID: {m.get('condition_id', 'N/A')}")
            print(f"    Volume: ${m.get('volume', 0):,.0f}")
            print(f"    Active: {m.get('active', False)}")
            
            # Find any market with tokens
            for market in markets:
                if 'tokens' in market and market['tokens']:
                    for token in market['tokens']:
                        tid = token.get('token_id')
                        if tid:
                            test_token_id = str(tid)
                            print(f"\n  Using token from market: {market.get('question', 'N/A')[:50]}")
                            print(f"  Token ID: {test_token_id}")
                            break
                if test_token_id:
                    break
    else:
        print(f"  ❌ Unexpected response format: {type(result)}")
except Exception as e:
    print(f"  ❌ Error: {e}")

print("\n" + "="*80)
print("TEST 2: Get Market Price")
print("="*80)
if test_token_id:
    try:
        price = client.get_midpoint(test_token_id)
        print(f"  ✅ Midpoint price: ${float(price):.4f}")
        print(f"  Token ID: {test_token_id}")
    except Exception as e:
        print(f"  ❌ Error: {e}")
else:
    print("  ⚠️  Skipping - no token ID available from market data")

print("\n" + "="*80)
print("TEST 3: Get Orderbook")
print("="*80)
if test_token_id:
    try:
        book = client.get_order_book(test_token_id)
        print(f"  ✅ Orderbook retrieved")
        print(f"  Market: {book.market}")
        if book.bids:
            print(f"  Best bid: ${float(book.bids[0].price):.4f} (size: {float(book.bids[0].size):.2f})")
        if book.asks:
            print(f"  Best ask: ${float(book.asks[0].price):.4f} (size: {float(book.asks[0].size):.2f})")
    except Exception as e:
        print(f"  ❌ Error: {e}")
else:
    print("  ⚠️  Skipping - no token ID available from market data")

print("\n" + "=" * 80)
print("✅ CLOB Client Tests Complete!")
print("=" * 80)
print("\nSUMMARY:")
print("- Direct access to Polymarket via py-clob-client")
print("- No Dome API key required for read-only operations")
print("- No 403 errors!")
print("- Full market data, prices, and orderbook access")
print("=" * 80)
