"""Get stock quote snapshot - daily summary with fundamentals"""
from ..api import fmp


def get_quote_snapshot(symbol: str):
    """
    Get stock quote snapshot (daily summary + fundamentals)
    
    Args:
        symbol: Stock ticker (or comma-separated: 'AAPL,MSFT,GOOGL')
        
    Returns:
        dict or list: symbol, name, price, change, changesPercentage, 
                      dayLow, dayHigh, volume, marketCap, pe, eps
                      
    Note: For real-time quotes, use polygon.market.quote instead.
          This is best for daily snapshots with PE, market cap, etc.
    """
    return fmp(f'/quote/{symbol}')
