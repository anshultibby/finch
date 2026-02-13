"""Get market movers - gainers, losers, most active"""
from ..api import fmp
from typing import List, Dict, Any


def get_gainers() -> List[Dict[str, Any]]:
    """
    Get biggest stock gainers of the day.
    
    Returns:
        List of dicts: symbol, name, price, change, changesPercentage
    
    Warning: Includes penny stocks. Filter by price > 10 and volume > 1M.
    """
    return fmp('/stock_market/gainers')


def get_losers() -> List[Dict[str, Any]]:
    """Get biggest stock losers of the day. Same fields as get_gainers()."""
    return fmp('/stock_market/losers')


def get_actives() -> List[Dict[str, Any]]:
    """Get most actively traded stocks by volume. Same fields as get_gainers()."""
    return fmp('/stock_market/actives')
