#!/usr/bin/env python3
"""
Test updated matching markets implementation
"""
import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add backend to path (we're in experiments/ subfolder)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

# Load environment
env_path = os.path.join(os.path.dirname(__file__), '..', 'backend', '.env')
load_dotenv(env_path)

from modules.tools.servers.dome.matching import get_sports_matching_markets, get_sport_by_date


def test_sport_by_date():
    """Test getting all markets for a sport/date"""
    print("="*80)
    print("TEST 1: Get all NBA markets for tomorrow")
    print("="*80)
    
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    result = get_sport_by_date(sport='nba', date=tomorrow)
    
    if 'error' in result:
        print(f"❌ Error: {result['error']}")
        return
    
    print(f"✅ Found {len(result.get('markets', {}))} market groups")
    print(f"Sport: {result.get('sport')}")
    print(f"Date: {result.get('date')}")
    
    # Show first 3 matches
    for i, (market_key, platforms) in enumerate(list(result['markets'].items())[:3]):
        print(f"\n  {i+1}. {market_key}")
        print(f"     Platforms: {len(platforms)}")
        for platform_data in platforms:
            platform = platform_data['platform']
            if platform == 'POLYMARKET':
                print(f"     • Polymarket: {platform_data['market_slug']}")
                print(f"       Token IDs: {len(platform_data.get('token_ids', []))}")
            elif platform == 'KALSHI':
                print(f"     • Kalshi: {platform_data['event_ticker']}")
                print(f"       Market Tickers: {len(platform_data.get('market_tickers', []))}")
    
    print()


def test_matching_by_slug():
    """Test getting matches by Polymarket slug"""
    print("="*80)
    print("TEST 2: Get matches by Polymarket slug")
    print("="*80)
    
    # Use a slug from the previous test
    slugs = ['nba-lal-nyk-2026-02-01']
    print(f"Querying for: {slugs}")
    
    result = get_sports_matching_markets(polymarket_market_slug=slugs)
    
    if 'error' in result:
        print(f"❌ Error: {result['error']}")
        return
    
    print(f"✅ Found {len(result.get('markets', {}))} matches")
    
    for market_key, platforms in result['markets'].items():
        print(f"\n  {market_key}")
        for platform_data in platforms:
            platform = platform_data['platform']
            if platform == 'POLYMARKET':
                print(f"    Polymarket: {platform_data['market_slug']}")
            elif platform == 'KALSHI':
                print(f"    Kalshi: {platform_data['event_ticker']}")
    
    print()


def test_matching_by_ticker():
    """Test getting matches by Kalshi ticker"""
    print("="*80)
    print("TEST 3: Get matches by Kalshi ticker")
    print("="*80)
    
    tickers = ['KXNBAGAME-26FEB01LALNYK']
    print(f"Querying for: {tickers}")
    
    result = get_sports_matching_markets(kalshi_event_ticker=tickers)
    
    if 'error' in result:
        print(f"❌ Error: {result['error']}")
        return
    
    print(f"✅ Found {len(result.get('markets', {}))} matches")
    
    for market_key, platforms in result['markets'].items():
        print(f"\n  {market_key}")
        for platform_data in platforms:
            platform = platform_data['platform']
            if platform == 'POLYMARKET':
                print(f"    Polymarket: {platform_data['market_slug']}")
            elif platform == 'KALSHI':
                print(f"    Kalshi: {platform_data['event_ticker']}")
    
    print()


def main():
    print("""
╔═══════════════════════════════════════════════════════════════════════════╗
║                                                                           ║
║              Test Updated Matching Markets Implementation                 ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝
    """)
    
    if not os.getenv('DOME_API_KEY'):
        print("❌ ERROR: DOME_API_KEY not found")
        return
    
    test_sport_by_date()
    test_matching_by_slug()
    test_matching_by_ticker()
    
    print("="*80)
    print("✅ All tests complete!")
    print("="*80)


if __name__ == "__main__":
    main()
