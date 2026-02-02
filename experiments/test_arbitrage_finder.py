#!/usr/bin/env python3
"""
Test the arbitrage opportunity finder
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

from modules.tools.servers.dome.matching import find_arbitrage_opportunities


def test_arbitrage_finder():
    """Test finding arbitrage opportunities"""
    print("""
╔═══════════════════════════════════════════════════════════════════════════╗
║                                                                           ║
║                  Arbitrage Opportunity Finder Test                        ║
║                                                                           ║
║  Searches for price differences across Polymarket and Kalshi             ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝
    """)
    
    if not os.getenv('DOME_API_KEY'):
        print("❌ ERROR: DOME_API_KEY not found")
        return
    
    # Test with NBA markets for tomorrow
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    
    print(f"Searching for NBA arbitrage opportunities on {tomorrow}...")
    print("(This will take a while due to rate limiting - 1 req/sec)")
    print()
    
    result = find_arbitrage_opportunities(
        sport='nba', 
        date=tomorrow,
        min_spread=0.03  # 3% minimum spread
    )
    
    if 'error' in result:
        print(f"❌ Error: {result['error']}")
        return
    
    print("="*80)
    print(f"Results for {result['sport'].upper()} on {result['date']}")
    print("="*80)
    print(f"Markets checked: {result['total_markets_checked']}")
    print(f"Opportunities found: {result['opportunities_found']}")
    print()
    
    if result['opportunities_found'] == 0:
        print("No arbitrage opportunities found with minimum 3% spread")
        print("(This is normal - efficient markets rarely have large spreads)")
        return
    
    print(f"Found {len(result['opportunities'])} arbitrage opportunities:\n")
    
    for i, opp in enumerate(result['opportunities'], 1):
        print(f"{i}. {opp['market_key']}")
        print(f"   Spread: {opp['spread']*100:.2f}%")
        print(f"   Polymarket: {opp['polymarket']['price']:.4f} ({opp['polymarket']['price']*100:.1f}%)")
        print(f"   Kalshi: {opp['kalshi']['price']:.4f} ({opp['kalshi']['price']*100:.1f}%)")
        print(f"   Strategy: {opp['arbitrage_type'].replace('_', ' ').title()}")
        print()
    
    print("="*80)
    print("✅ Test complete!")
    print("="*80)


if __name__ == "__main__":
    test_arbitrage_finder()
