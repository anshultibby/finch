"""
Sports Market Matching - Cross-platform Arbitrage

Find matching sports markets across Polymarket and Kalshi.
"""
from typing import Optional, Dict, Any
from .._client import call_dome_api


def get_sports_matching_markets(
    sport: Optional[str] = None,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Find matching sports markets across Polymarket and Kalshi.
    
    Args:
        sport: Filter by sport (e.g., 'NBA', 'NFL', 'MLB', 'NHL')
        limit: Number of results to return (1-100, default 10)
        
    Returns:
        dict with:
        - matches: List of matched markets across platforms
            Each match contains:
            - polymarket: Polymarket market data (if exists)
            - kalshi: Kalshi market data (if exists)
            - sport: Sport category
            - event_description: What the market is about
            
    Example:
        # Find NBA markets on both platforms
        matches = get_sports_matching_markets(sport='NBA', limit=20)
        if 'error' not in matches:
            for match in matches['matches']:
                poly = match.get('polymarket', {})
                kal = match.get('kalshi', {})
                
                print(f"\n{match['event_description']}")
                if poly:
                    print(f"  Polymarket: {poly.get('price', 'N/A')}")
                if kal:
                    print(f"  Kalshi: {kal.get('price', 'N/A')}¢")
                    
                # Calculate arbitrage opportunity
                if poly and kal:
                    poly_prob = poly.get('price', 0)
                    kal_prob = kal.get('price', 0) / 100
                    diff = abs(poly_prob - kal_prob)
                    if diff > 0.05:
                        print(f"  ⚠️ Price difference: {diff*100:.1f}%")
    """
    params = {
        "limit": min(max(1, limit), 100)
    }
    
    if sport:
        params["sport"] = sport
    
    return call_dome_api("/matching-markets/sports", params)


def get_sport_by_date(
    sport: str,
    date: str
) -> Dict[str, Any]:
    """
    Find matching sports markets for a specific sport on a specific date.
    
    More precise than get_sports_matching_markets - useful for finding markets
    for games happening on a particular day.
    
    Args:
        sport: Sport name (e.g., 'NBA', 'NFL', 'MLB', 'NHL')
        date: Date in YYYY-MM-DD format (e.g., '2024-12-25')
        
    Returns:
        dict with:
        - sport: Sport name
        - date: Date
        - matches: List of matched markets for games on that date
            Each match contains:
            - polymarket: Polymarket market data (if exists)
            - kalshi: Kalshi market data (if exists)
            - event_description: Game/event description
            - game_time: Scheduled game time (if available)
            
    Example:
        # Find all NBA markets for Christmas Day
        matches = get_sport_by_date(sport='NBA', date='2024-12-25')
        if 'error' not in matches:
            print(f"NBA games on {matches['date']}:")
            for match in matches['matches']:
                print(f"\n{match['event_description']}")
                if 'game_time' in match:
                    print(f"  Game time: {match['game_time']}")
                
                poly = match.get('polymarket', {})
                kal = match.get('kalshi', {})
                if poly:
                    print(f"  Polymarket: {poly.get('price', 'N/A')}")
                if kal:
                    print(f"  Kalshi: {kal.get('price', 'N/A')}¢")
        
        # Check tomorrow's NFL games
        from datetime import datetime, timedelta
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        matches = get_sport_by_date(sport='NFL', date=tomorrow)
    """
    endpoint = f"/matching-markets/sports/{sport}"
    params = {"date": date}
    
    return call_dome_api(endpoint, params)
