"""Get stock quote with fundamentals (PE, EPS, market cap)"""
from ..api import fmp
from typing import List, Dict, Any, Union


def get_quote_snapshot(symbol: str) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Get stock quote snapshot with fundamentals.
    
    Args:
        symbol: Stock ticker ('AAPL') or comma-separated ('AAPL,MSFT,GOOGL')
    
    Returns:
        LIST of dicts (even for single stock!) with:
        symbol, name, price, change, changesPercentage, dayLow, dayHigh,
        yearLow, yearHigh, volume, avgVolume, marketCap, pe, eps, open,
        previousClose, exchange
    
    Usage:
        quote = get_quote_snapshot('AAPL')[0]  # Use [0] for single stock
        quotes = get_quote_snapshot('AAPL,MSFT')  # Multiple stocks
    """
    return fmp(f'/quote/{symbol}')
