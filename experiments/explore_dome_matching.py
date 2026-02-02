#!/usr/bin/env python3
"""
Dome API Market Matching Exploration Script

Tests all matching market endpoints and demonstrates their capabilities:
1. Get matching markets by sport/date
2. Get matching markets by specific Polymarket slugs
3. Get matching markets by specific Kalshi tickers

This explores arbitrage opportunities across prediction market platforms.
"""
import os
import sys
import time
from typing import Optional, List, Dict, Any
import httpx
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables from backend/.env (we're in experiments/ subfolder)
env_path = os.path.join(os.path.dirname(__file__), '..', 'backend', '.env')
load_dotenv(env_path)


class RateLimiter:
    """Simple rate limiter for Dome API (1 req/sec)"""
    
    def __init__(self, requests_per_second: float = 1.0):
        self.min_interval = 1.0 / requests_per_second
        self.last_request_time = 0.0
    
    def wait(self):
        """Wait until we can make another request"""
        now = time.time()
        time_since_last = now - self.last_request_time
        
        if time_since_last < self.min_interval:
            wait_time = self.min_interval - time_since_last
            time.sleep(wait_time)
        
        self.last_request_time = time.time()


_rate_limiter = RateLimiter(requests_per_second=1.0)


def call_dome_api(endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Call Dome API with rate limiting and error handling."""
    api_key = os.getenv('DOME_API_KEY')
    if not api_key:
        return {"error": "DOME_API_KEY not found in environment variables"}
    
    _rate_limiter.wait()
    
    url = f"https://api.domeapi.io/v1{endpoint}"
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                url,
                headers={'x-api-key': api_key},
                params=params
            )
            response.raise_for_status()
            return response.json()
    
    except httpx.HTTPStatusError as e:
        return {"error": f"HTTP {e.response.status_code}: {e.response.text}"}
    except httpx.RequestError as e:
        return {"error": f"Request failed: {str(e)}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}


def print_separator(title: str = ""):
    """Print a nice separator with optional title"""
    if title:
        print(f"\n{'='*80}")
        print(f" {title}")
        print(f"{'='*80}\n")
    else:
        print(f"\n{'-'*80}\n")


def explore_sport_by_date():
    """Explore matching markets by sport and date"""
    print_separator("TEST 1: Get Matching Markets by Sport and Date")
    
    # Test with NFL markets for a recent date
    today = datetime.now()
    # Try today and next few days to find active markets
    for days_ahead in range(7):
        test_date = (today + timedelta(days=days_ahead)).strftime('%Y-%m-%d')
        
        print(f"Searching NFL markets on {test_date}...")
        result = call_dome_api(f"/matching-markets/sports/nfl", {"date": test_date})
        
        if 'error' in result:
            print(f"  ❌ Error: {result['error']}")
            continue
        
        if result.get('markets'):
            print(f"  ✅ Found {len(result['markets'])} matching market groups")
            print(f"  Sport: {result.get('sport', 'N/A')}")
            print(f"  Date: {result.get('date', 'N/A')}")
            
            # Show first match in detail
            for market_key, platforms in list(result['markets'].items())[:1]:
                print(f"\n  Example match: {market_key}")
                for platform_data in platforms:
                    platform = platform_data.get('platform', 'UNKNOWN')
                    print(f"    {platform}:")
                    if platform == 'POLYMARKET':
                        print(f"      Market Slug: {platform_data.get('market_slug')}")
                        token_ids = platform_data.get('token_ids', [])
                        print(f"      Token IDs: {len(token_ids)} tokens")
                    elif platform == 'KALSHI':
                        print(f"      Event Ticker: {platform_data.get('event_ticker')}")
                        tickers = platform_data.get('market_tickers', [])
                        print(f"      Market Tickers: {len(tickers)} markets")
            break
        else:
            print(f"  No markets found for {test_date}")
    
    print_separator()


def explore_by_polymarket_slug():
    """Explore matching markets by specific Polymarket slug"""
    print_separator("TEST 2: Get Matching Markets by Polymarket Slug")
    
    # First, let's get some active Polymarket sports markets
    print("Step 1: Finding active Polymarket sports markets...")
    markets_result = call_dome_api("/polymarket/markets", {
        "tags": ["sports"],
        "status": "open",
        "limit": 5
    })
    
    if 'error' in markets_result:
        print(f"❌ Error getting markets: {markets_result['error']}")
        return
    
    markets = markets_result.get('markets', [])
    if not markets:
        print("No active sports markets found")
        return
    
    print(f"✅ Found {len(markets)} active sports markets\n")
    
    # Try to find matches for these slugs
    slugs = [m['market_slug'] for m in markets[:3]]
    print(f"Step 2: Finding matches for slugs: {slugs}")
    
    # Build query params for multiple slugs
    params = {}
    for i, slug in enumerate(slugs):
        params[f'polymarket_market_slug'] = slug if i == 0 else params.get('polymarket_market_slug', [])
        if i > 0:
            if not isinstance(params['polymarket_market_slug'], list):
                params['polymarket_market_slug'] = [params['polymarket_market_slug']]
            params['polymarket_market_slug'].append(slug)
    
    result = call_dome_api("/matching-markets/sports", params)
    
    if 'error' in result:
        print(f"❌ Error: {result['error']}")
        return
    
    matched_markets = result.get('markets', {})
    print(f"\n✅ Found {len(matched_markets)} matched market groups")
    
    for market_key, platforms in matched_markets.items():
        print(f"\n  Match: {market_key}")
        print(f"  Platforms: {len(platforms)}")
        for platform_data in platforms:
            platform = platform_data.get('platform', 'UNKNOWN')
            print(f"    • {platform}")
            if platform == 'POLYMARKET':
                print(f"      Slug: {platform_data.get('market_slug')}")
            elif platform == 'KALSHI':
                print(f"      Ticker: {platform_data.get('event_ticker')}")
    
    print_separator()


def explore_by_kalshi_ticker():
    """Explore matching markets by specific Kalshi ticker"""
    print_separator("TEST 3: Get Matching Markets by Kalshi Ticker")
    
    # Get some active Kalshi markets
    print("Step 1: Finding active Kalshi markets...")
    markets_result = call_dome_api("/kalshi/markets", {
        "status": "active",
        "limit": 5
    })
    
    if 'error' in markets_result:
        print(f"❌ Error getting markets: {markets_result['error']}")
        return
    
    markets = markets_result.get('markets', [])
    if not markets:
        print("No active Kalshi markets found")
        return
    
    print(f"✅ Found {len(markets)} active Kalshi markets")
    
    # Try to extract event tickers (they follow pattern like KXNFLGAME-25AUG16ARIDEN)
    # Market ticker format: {EVENT_TICKER}-{OUTCOME}
    event_tickers = set()
    for market in markets:
        ticker = market.get('ticker', '')
        # Extract event ticker (everything before last dash)
        if '-' in ticker:
            parts = ticker.rsplit('-', 1)
            if len(parts) == 2:
                event_tickers.add(parts[0])
    
    if not event_tickers:
        print("Could not extract event tickers from markets")
        return
    
    event_tickers = list(event_tickers)[:3]
    print(f"\nStep 2: Finding matches for event tickers: {event_tickers}\n")
    
    # Build query params
    params = {}
    for i, ticker in enumerate(event_tickers):
        if i == 0:
            params['kalshi_event_ticker'] = ticker
        else:
            if not isinstance(params.get('kalshi_event_ticker'), list):
                params['kalshi_event_ticker'] = [params['kalshi_event_ticker']]
            params['kalshi_event_ticker'].append(ticker)
    
    result = call_dome_api("/matching-markets/sports", params)
    
    if 'error' in result:
        print(f"❌ Error: {result['error']}")
        return
    
    matched_markets = result.get('markets', {})
    print(f"✅ Found {len(matched_markets)} matched market groups")
    
    for market_key, platforms in matched_markets.items():
        print(f"\n  Match: {market_key}")
        for platform_data in platforms:
            platform = platform_data.get('platform', 'UNKNOWN')
            print(f"    • {platform}")
            if platform == 'POLYMARKET':
                print(f"      Slug: {platform_data.get('market_slug')}")
            elif platform == 'KALSHI':
                print(f"      Ticker: {platform_data.get('event_ticker')}")
    
    print_separator()


def explore_arbitrage_opportunities():
    """Find and display arbitrage opportunities"""
    print_separator("TEST 4: Arbitrage Opportunity Detection")
    
    print("Searching for arbitrage opportunities across platforms...\n")
    
    # Get NBA markets (typically have good liquidity on both platforms)
    today = datetime.now()
    for days_ahead in range(7):
        test_date = (today + timedelta(days=days_ahead)).strftime('%Y-%m-%d')
        
        result = call_dome_api(f"/matching-markets/sports/nba", {"date": test_date})
        
        if 'error' in result or not result.get('markets'):
            continue
        
        print(f"Checking markets on {test_date}...")
        
        matched_markets = result.get('markets', {})
        for market_key, platforms in matched_markets.items():
            # Check if we have both platforms
            poly_data = None
            kalshi_data = None
            
            for platform_data in platforms:
                if platform_data.get('platform') == 'POLYMARKET':
                    poly_data = platform_data
                elif platform_data.get('platform') == 'KALSHI':
                    kalshi_data = platform_data
            
            if poly_data and kalshi_data:
                print(f"\n  Found cross-platform market: {market_key}")
                print(f"    Polymarket: {poly_data.get('market_slug')}")
                print(f"    Kalshi: {kalshi_data.get('event_ticker')}")
                
                # Could fetch prices here and calculate spreads
                # For now just showing the structure
                print(f"    ✅ Available on both platforms - check prices for arbitrage")
        
        if matched_markets:
            break
    
    print_separator()


def main():
    """Run all exploration tests"""
    print("""
╔═══════════════════════════════════════════════════════════════════════════╗
║                                                                           ║
║           Dome API Market Matching Exploration Script                    ║
║                                                                           ║
║  This script demonstrates all market matching capabilities:              ║
║  • Find markets by sport and date                                        ║
║  • Match specific Polymarket slugs to Kalshi                             ║
║  • Match specific Kalshi tickers to Polymarket                           ║
║  • Identify cross-platform arbitrage opportunities                       ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝
    """)
    
    # Check API key
    if not os.getenv('DOME_API_KEY'):
        print("❌ ERROR: DOME_API_KEY not found in environment")
        print("   Please set it in your .env file or export it")
        return
    
    try:
        # Run all exploration tests
        explore_sport_by_date()
        explore_by_polymarket_slug()
        explore_by_kalshi_ticker()
        explore_arbitrage_opportunities()
        
        print("""
╔═══════════════════════════════════════════════════════════════════════════╗
║                                                                           ║
║                          EXPLORATION COMPLETE                             ║
║                                                                           ║
║  Key Findings:                                                            ║
║  • Matching markets API supports both date-based and slug/ticker lookup  ║
║  • Can query multiple market slugs/tickers at once                       ║
║  • Response format provides clean mapping between platforms              ║
║  • Useful for arbitrage detection and cross-platform price comparison    ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝
        """)
        
    except KeyboardInterrupt:
        print("\n\n❌ Exploration interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
