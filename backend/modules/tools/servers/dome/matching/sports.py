"""
Sports Market Matching - Cross-platform Arbitrage

Find matching sports markets across Polymarket and Kalshi.

TODO: Add Pydantic models for return types (GetSportsMatchingOutput, GetArbitrageOutput)
"""
from typing import Optional, List, Literal
from .._client import call_dome_api
from ..polymarket.prices import get_market_price as get_polymarket_price
from ..kalshi.markets import get_market_price as get_kalshi_price
from ..models import GetMarketPriceInput, GetKalshiMarketPriceInput


def get_sports_matching_markets(
    polymarket_market_slug: Optional[List[str]] = None,
    kalshi_event_ticker: Optional[List[str]] = None,
) -> dict:
    """
    Find matching sports markets across Polymarket and Kalshi by specific identifiers.
    
    Query by either Polymarket market slugs OR Kalshi event tickers (not both).
    Use get_sport_by_date() to find all matches for a specific sport/date instead.
    
    Args:
        polymarket_market_slug: List of Polymarket market slugs to find matches for
                                (e.g., ['nba-lal-gsw-2026-02-01'])
                                Cannot be combined with kalshi_event_ticker
        kalshi_event_ticker: List of Kalshi event tickers to find matches for
                            (e.g., ['KXNBAGAME-26FEB01LALGSW'])
                            Cannot be combined with polymarket_market_slug
        
    Returns:
        dict with:
        - markets: Dict mapping market keys to platform data arrays
            Each key (e.g., 'nba-lal-gsw-2026-02-01') maps to array of:
            - platform: 'POLYMARKET' or 'KALSHI'
            - For POLYMARKET:
                - market_slug: Polymarket market slug
                - token_ids: Array of token IDs for each outcome
            - For KALSHI:
                - event_ticker: Kalshi event ticker
                - market_tickers: Array of market tickers for each outcome
            
    Example:
        # Find matches for specific Polymarket markets
        result = get_sports_matching_markets(
            polymarket_market_slug=['nba-lal-gsw-2026-02-01', 'nfl-kc-buf-2026-02-09']
        )
        if 'error' not in result:
            for market_key, platforms in result['markets'].items():
                print(f"\nMarket: {market_key}")
                for platform_data in platforms:
                    if platform_data['platform'] == 'POLYMARKET':
                        print(f"  Polymarket: {platform_data['market_slug']}")
                    elif platform_data['platform'] == 'KALSHI':
                        print(f"  Kalshi: {platform_data['event_ticker']}")
        
        # Find matches for specific Kalshi events
        result = get_sports_matching_markets(
            kalshi_event_ticker=['KXNBAGAME-26FEB01LALGSW']
        )
    """
    if polymarket_market_slug and kalshi_event_ticker:
        return {"error": "Cannot combine polymarket_market_slug and kalshi_event_ticker"}
    
    if not polymarket_market_slug and not kalshi_event_ticker:
        return {"error": "Must provide either polymarket_market_slug or kalshi_event_ticker"}
    
    params = {}
    
    if polymarket_market_slug:
        # API expects multiple query params with same name
        params['polymarket_market_slug'] = polymarket_market_slug
    
    if kalshi_event_ticker:
        params['kalshi_event_ticker'] = kalshi_event_ticker
    
    return call_dome_api("/matching-markets/sports", params)


def get_sport_by_date(
    sport: Literal["nfl", "mlb", "cfb", "nba", "nhl", "cbb", "pga", "tennis"],
    date: str
) -> dict:
    """
    Find all matching sports markets for a specific sport on a specific date.
    
    This returns ALL markets for games happening on that date, making it easy
    to discover arbitrage opportunities across platforms.
    
    Args:
        sport: Sport abbreviation (lowercase):
            - 'nfl': Football
            - 'mlb': Baseball  
            - 'cfb': College Football
            - 'nba': Basketball
            - 'nhl': Hockey
            - 'cbb': College Basketball
            - 'pga': Golf
            - 'tennis': Tennis
        date: Date in YYYY-MM-DD format (e.g., '2026-02-01')
        
    Returns:
        dict with:
        - sport: Sport abbreviation
        - date: Date string
        - markets: Dict mapping market keys to platform data arrays
            Each key (e.g., 'nba-lal-gsw-2026-02-01') maps to array of:
            - platform: 'POLYMARKET' or 'KALSHI'
            - For POLYMARKET:
                - market_slug: Polymarket market slug
                - token_ids: Array of token IDs for each outcome
            - For KALSHI:
                - event_ticker: Kalshi event ticker
                - market_tickers: Array of market tickers for each outcome
            
    Example:
        # Find all NBA markets for a specific date
        result = get_sport_by_date(sport='nba', date='2026-02-01')
        if 'error' not in result:
            print(f"NBA games on {result['date']}:")
            for market_key, platforms in result['markets'].items():
                print(f"\n{market_key}:")
                
                # Check if available on both platforms (arbitrage opportunity!)
                has_poly = any(p['platform'] == 'POLYMARKET' for p in platforms)
                has_kalshi = any(p['platform'] == 'KALSHI' for p in platforms)
                
                if has_poly and has_kalshi:
                    print("  ✅ Available on both platforms - potential arbitrage")
                
                for platform_data in platforms:
                    platform = platform_data['platform']
                    if platform == 'POLYMARKET':
                        print(f"  Polymarket: {platform_data['market_slug']}")
                    elif platform == 'KALSHI':
                        print(f"  Kalshi: {platform_data['event_ticker']}")
        
        # Check tomorrow's games
        from datetime import datetime, timedelta
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        result = get_sport_by_date(sport='nfl', date=tomorrow)
    """
    endpoint = f"/matching-markets/sports/{sport}"
    params = {"date": date}
    
    return call_dome_api(endpoint, params)


def find_arbitrage_opportunities(
    sport: Literal["nfl", "mlb", "cfb", "nba", "nhl", "cbb", "pga", "tennis"],
    date: str,
    min_spread: float = 0.05
) -> dict:
    """
    Find arbitrage opportunities by comparing prices across Polymarket and Kalshi.
    
    This function:
    1. Gets all matching markets for a sport/date
    2. Fetches current prices from both platforms
    3. Calculates spreads and identifies opportunities
    
    Args:
        sport: Sport abbreviation (e.g., 'nba', 'nfl')
        date: Date in YYYY-MM-DD format
        min_spread: Minimum price difference to report (default 0.05 = 5%)
        
    Returns:
        dict with:
        - sport: Sport abbreviation
        - date: Date string
        - opportunities: List of dicts with:
            - market_key: Market identifier
            - polymarket: Dict with market_slug, token_id, price
            - kalshi: Dict with event_ticker, market_ticker, price
            - spread: Price difference (absolute value)
            - arbitrage_type: 'buy_poly_sell_kalshi' or 'buy_kalshi_sell_poly'
            
    Example:
        # Find NBA arbitrage opportunities for tomorrow
        from datetime import datetime, timedelta
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        
        result = find_arbitrage_opportunities(sport='nba', date=tomorrow, min_spread=0.03)
        
        if 'error' not in result:
            print(f"Found {len(result['opportunities'])} arbitrage opportunities:")
            for opp in result['opportunities']:
                print(f"\n{opp['market_key']}")
                print(f"  Spread: {opp['spread']*100:.1f}%")
                print(f"  Polymarket: {opp['polymarket']['price']:.3f}")
                print(f"  Kalshi: {opp['kalshi']['price']:.3f}")
                print(f"  Strategy: {opp['arbitrage_type']}")
    """
    # Get all matching markets
    matches = get_sport_by_date(sport=sport, date=date)
    
    if 'error' in matches:
        return matches
    
    opportunities = []
    
    for market_key, platforms in matches.get('markets', {}).items():
        # Check if available on both platforms
        poly_data = None
        kalshi_data = None
        
        for platform_info in platforms:
            if platform_info['platform'] == 'POLYMARKET':
                poly_data = platform_info
            elif platform_info['platform'] == 'KALSHI':
                kalshi_data = platform_info
        
        if not (poly_data and kalshi_data):
            continue  # Skip if not on both platforms
        
        # Get prices (using first token/ticker - typically the "Yes" side)
        poly_token_id = poly_data.get('token_ids', [None])[0]
        kalshi_ticker = kalshi_data.get('market_tickers', [None])[0]
        
        if not poly_token_id or not kalshi_ticker:
            continue
        
        # Fetch prices
        try:
            poly_price_result = get_polymarket_price(GetMarketPriceInput(token_id=poly_token_id))
            kalshi_price_result = get_kalshi_price(GetKalshiMarketPriceInput(ticker=kalshi_ticker))
            
            # Polymarket price is 0-1, Kalshi price is 0-100 cents
            poly_price = poly_price_result.price
            kalshi_price = kalshi_price_result.price / 100.0
        except Exception:
            continue
        
        spread = abs(poly_price - kalshi_price)
        
        if spread >= min_spread:
            # Determine arbitrage direction
            if poly_price < kalshi_price:
                arb_type = 'buy_poly_sell_kalshi'
            else:
                arb_type = 'buy_kalshi_sell_poly'
            
            opportunities.append({
                'market_key': market_key,
                'polymarket': {
                    'market_slug': poly_data['market_slug'],
                    'token_id': poly_token_id,
                    'price': poly_price
                },
                'kalshi': {
                    'event_ticker': kalshi_data['event_ticker'],
                    'market_ticker': kalshi_ticker,
                    'price': kalshi_price
                },
                'spread': spread,
                'arbitrage_type': arb_type
            })
    
    return {
        'sport': sport,
        'date': date,
        'opportunities': opportunities,
        'total_markets_checked': len(matches.get('markets', {})),
        'opportunities_found': len(opportunities)
    }
