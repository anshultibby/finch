"""
Market Movers - Gainers, Losers, Most Active

Functions:
    get_gainers() - Biggest stock gainers of the day
    get_losers() - Biggest stock losers of the day
    get_actives() - Most actively traded stocks

Example:
    from servers.financial_modeling_prep.market.gainers import get_gainers, get_losers
    
    # Get today's top gainers
    gainers = get_gainers()
    # Returns: [{'symbol': 'XYZ', 'name': 'XYZ Corp', 'price': 10.50,
    #            'change': 2.10, 'changesPercentage': 25.0, ...}, ...]
    
    # Filter for liquid stocks
    liquid_gainers = [g for g in gainers 
                      if g.get('volume', 0) > 1000000 
                      and g.get('price', 0) > 5]

Note:
    - Returns raw market data - many will be low-liquidity penny stocks
    - Always filter by volume and price for tradeable stocks
    - Best combined with get_quote_snapshot() for detailed analysis
"""
from ..api import fmp
from typing import List, Dict, Any


def get_gainers() -> List[Dict[str, Any]]:
    """
    Get the biggest stock gainers of the day.
    
    Returns:
        List of dicts, each with keys:
            - symbol: str - Ticker symbol
            - name: str - Company name
            - price: float - Current price
            - change: float - Dollar change
            - changesPercentage: float - Percent change
    
    Example:
        >>> gainers = get_gainers()
        >>> # Filter for tradeable stocks (high volume, reasonable price)
        >>> tradeable = [g for g in gainers 
        ...              if g.get('price', 0) > 10 
        ...              and g.get('changesPercentage', 0) > 5]
        >>> for g in tradeable[:5]:
        ...     print(f"{g['symbol']}: +{g['changesPercentage']:.1f}%")
    
    Warning:
        - Raw results include many illiquid/penny stocks
        - Always filter by price and volume before trading
    """
    return fmp('/stock_market/gainers')


def get_losers() -> List[Dict[str, Any]]:
    """
    Get the biggest stock losers of the day.
    
    Returns:
        List of dicts with same structure as get_gainers()
    
    Example:
        >>> losers = get_losers()
        >>> big_losers = [l for l in losers 
        ...               if l.get('price', 0) > 10
        ...               and l.get('changesPercentage', 0) < -5]
    """
    return fmp('/stock_market/losers')


def get_actives() -> List[Dict[str, Any]]:
    """
    Get the most actively traded stocks by volume.
    
    Returns:
        List of dicts with same structure as get_gainers()
    
    Example:
        >>> actives = get_actives()
        >>> print("Most active stocks today:")
        >>> for a in actives[:10]:
        ...     print(f"{a['symbol']}: {a.get('volume', 0):,} shares")
    """
    return fmp('/stock_market/actives')
