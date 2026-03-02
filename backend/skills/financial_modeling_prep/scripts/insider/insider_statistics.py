"""Get insider trading statistics - aggregated buy/sell summary"""
from ..api import fmp


def get_insider_statistics(symbol: str):
    """
    Get aggregated insider trading statistics.
    
    Args:
        symbol: Stock ticker (e.g., 'AAPL')
        
    Returns:
        Dict with totalBought, totalSold, buyCount, sellCount, etc.
    """
    return fmp('/insider-trading-statistics', {'symbol': symbol})
