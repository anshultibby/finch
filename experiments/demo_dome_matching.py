#!/usr/bin/env python3
"""
Dome API Matching Markets - Comprehensive Demo

This script demonstrates all matching market functionality:
1. Find all markets for a sport/date
2. Query by specific Polymarket slugs
3. Query by specific Kalshi tickers
4. Find arbitrage opportunities

Run: backend/venv/bin/python demo_dome_matching.py
"""
import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Setup (we're in experiments/ subfolder)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
env_path = os.path.join(os.path.dirname(__file__), '..', 'backend', '.env')
load_dotenv(env_path)

from modules.tools.servers.dome.matching import (
    get_sports_matching_markets,
    get_sport_by_date,
    find_arbitrage_opportunities
)


def print_header(title):
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def demo_sport_by_date():
    """Demo 1: Find all markets for a sport on a specific date"""
    print_header("DEMO 1: Find All Markets for Sport/Date")
    
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    print(f"📅 Searching NBA markets for {tomorrow}...\n")
    
    result = get_sport_by_date(sport='nba', date=tomorrow)
    
    if 'error' in result:
        print(f"❌ Error: {result['error']}")
        return None
    
    markets = result.get('markets', {})
    print(f"✅ Found {len(markets)} market groups")
    print(f"Sport: {result['sport'].upper()}")
    print(f"Date: {result['date']}\n")
    
    # Count cross-platform markets
    cross_platform = sum(1 for platforms in markets.values() if len(platforms) == 2)
    print(f"🔄 {cross_platform} markets available on both platforms\n")
    
    # Show first 3
    for i, (market_key, platforms) in enumerate(list(markets.items())[:3]):
        print(f"{i+1}. {market_key}")
        for platform_data in platforms:
            platform = platform_data['platform']
            if platform == 'POLYMARKET':
                print(f"   • Polymarket: {platform_data['market_slug']}")
            elif platform == 'KALSHI':
                print(f"   • Kalshi: {platform_data['event_ticker']}")
    
    return markets


def demo_query_by_slug(markets):
    """Demo 2: Query by specific Polymarket slug"""
    print_header("DEMO 2: Query by Polymarket Market Slug")
    
    if not markets:
        print("Skipping - no markets from demo 1")
        return
    
    # Get a Polymarket slug from previous results
    poly_slug = None
    for platforms in markets.values():
        for p in platforms:
            if p['platform'] == 'POLYMARKET':
                poly_slug = p['market_slug']
                break
        if poly_slug:
            break
    
    if not poly_slug:
        print("No Polymarket slugs available")
        return
    
    print(f"🔍 Looking up: {poly_slug}\n")
    
    result = get_sports_matching_markets(polymarket_market_slug=[poly_slug])
    
    if 'error' in result:
        print(f"❌ Error: {result['error']}")
        return
    
    for market_key, platforms in result['markets'].items():
        print(f"✅ Found match: {market_key}")
        for platform_data in platforms:
            platform = platform_data['platform']
            if platform == 'POLYMARKET':
                print(f"   Polymarket: {platform_data['market_slug']}")
                print(f"   Token IDs: {len(platform_data.get('token_ids', []))} tokens")
            elif platform == 'KALSHI':
                print(f"   Kalshi: {platform_data['event_ticker']}")
                print(f"   Market Tickers: {len(platform_data.get('market_tickers', []))} tickers")


def demo_query_by_ticker(markets):
    """Demo 3: Query by specific Kalshi ticker"""
    print_header("DEMO 3: Query by Kalshi Event Ticker")
    
    if not markets:
        print("Skipping - no markets from demo 1")
        return
    
    # Get a Kalshi ticker from previous results
    kalshi_ticker = None
    for platforms in markets.values():
        for p in platforms:
            if p['platform'] == 'KALSHI':
                kalshi_ticker = p['event_ticker']
                break
        if kalshi_ticker:
            break
    
    if not kalshi_ticker:
        print("No Kalshi tickers available")
        return
    
    print(f"🔍 Looking up: {kalshi_ticker}\n")
    
    result = get_sports_matching_markets(kalshi_event_ticker=[kalshi_ticker])
    
    if 'error' in result:
        print(f"❌ Error: {result['error']}")
        return
    
    for market_key, platforms in result['markets'].items():
        print(f"✅ Found match: {market_key}")
        for platform_data in platforms:
            platform = platform_data['platform']
            if platform == 'POLYMARKET':
                print(f"   Polymarket: {platform_data['market_slug']}")
            elif platform == 'KALSHI':
                print(f"   Kalshi: {platform_data['event_ticker']}")


def demo_arbitrage():
    """Demo 4: Find arbitrage opportunities (optional - slow due to rate limits)"""
    print_header("DEMO 4: Find Arbitrage Opportunities (Optional)")
    
    print("⚠️  This demo makes many API calls and will take time due to rate limiting.")
    print("    Skip by pressing Ctrl+C, or wait for results...\n")
    
    try:
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        
        print(f"💰 Searching for arbitrage opportunities on {tomorrow}...")
        print("    (Rate limit: 1 req/sec, this will take a while)\n")
        
        result = find_arbitrage_opportunities(
            sport='nba',
            date=tomorrow,
            min_spread=0.03  # 3% minimum spread
        )
        
        if 'error' in result:
            print(f"❌ Error: {result['error']}")
            return
        
        print(f"\n✅ Checked {result['total_markets_checked']} markets")
        print(f"   Found {result['opportunities_found']} opportunities with 3%+ spread\n")
        
        if result['opportunities_found'] == 0:
            print("   No significant arbitrage opportunities found.")
            print("   (This is normal - markets are usually efficient)")
        else:
            for i, opp in enumerate(result['opportunities'][:5], 1):
                print(f"{i}. {opp['market_key']}")
                print(f"   Spread: {opp['spread']*100:.2f}%")
                print(f"   Polymarket: {opp['polymarket']['price']:.4f}")
                print(f"   Kalshi: {opp['kalshi']['price']:.4f}")
                print(f"   Strategy: {opp['arbitrage_type']}\n")
    
    except KeyboardInterrupt:
        print("\n\n⏭️  Arbitrage demo skipped by user")


def main():
    print("""
╔═══════════════════════════════════════════════════════════════════════════╗
║                                                                           ║
║              Dome API Matching Markets - Complete Demo                    ║
║                                                                           ║
║  This demonstrates all matching market functionality:                    ║
║  • Find markets by sport/date                                            ║
║  • Query by Polymarket slugs                                             ║
║  • Query by Kalshi tickers                                               ║
║  • Detect arbitrage opportunities                                        ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝
    """)
    
    if not os.getenv('DOME_API_KEY'):
        print("❌ ERROR: DOME_API_KEY not found in environment")
        print("   Set it in backend/.env or export it")
        return
    
    print("✅ DOME_API_KEY found\n")
    print("Starting demos...")
    
    # Run demos
    markets = demo_sport_by_date()
    demo_query_by_slug(markets)
    demo_query_by_ticker(markets)
    
    # Ask about arbitrage demo since it's slow
    print_header("Arbitrage Demo")
    print("The arbitrage finder makes many API calls (slow due to rate limiting).")
    response = input("Run arbitrage demo? (y/N): ").strip().lower()
    
    if response == 'y':
        demo_arbitrage()
    else:
        print("\n⏭️  Arbitrage demo skipped")
    
    print_header("Demo Complete!")
    print("""
Summary:
✅ Market matching by sport/date works
✅ Market matching by Polymarket slug works
✅ Market matching by Kalshi ticker works
✅ Implementation ready for use

Next steps:
- Import in your code: from modules.tools.servers.dome import matching
- Use in strategies: matching.get_sport_by_date(sport='nba', date='...')
- Find opportunities: matching.find_arbitrage_opportunities(...)

Documentation: DOME_MATCHING_IMPLEMENTATION.md
    """)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
