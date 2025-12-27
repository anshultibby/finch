"""Get last trade and current quote"""
from .._client import call_polygon_api


def get_last_trade(symbol: str):
    """
    Get last trade
    
    Args:
        symbol: Stock ticker
        
    Returns:
        dict: price, size, exchange, timestamp
    """
    result = call_polygon_api(f"/v2/last/trade/{symbol.upper()}")
    
    if 'error' in result:
        return result
    
    trade = result.get('results', {})
    return {
        'symbol': symbol.upper(),
        'price': trade.get('p'),
        'size': trade.get('s'),
        'exchange': trade.get('x'),
        'timestamp': trade.get('t'),
        'conditions': trade.get('c', [])
    }


def get_last_quote(symbol: str):
    """
    Get last quote (bid/ask)
    
    Args:
        symbol: Stock ticker
        
    Returns:
        dict: bid_price, bid_size, ask_price, ask_size, timestamp
    """
    result = call_polygon_api(f"/v2/last/nbbo/{symbol.upper()}")
    
    if 'error' in result:
        return result
    
    quote = result.get('results', {})
    return {
        'symbol': symbol.upper(),
        'bid_price': quote.get('p'),
        'bid_size': quote.get('s'),
        'ask_price': quote.get('P'),
        'ask_size': quote.get('S'),
        'timestamp': quote.get('t')
    }


def get_snapshot(symbol: str):
    """
    Get current snapshot including price, change, volume
    
    Args:
        symbol: Stock ticker
        
    Returns:
        dict: Current market snapshot
    """
    result = call_polygon_api(f"/v2/snapshot/locale/us/markets/stocks/tickers/{symbol.upper()}")
    
    if 'error' in result:
        return result
    
    ticker = result.get('ticker', {})
    day = ticker.get('day', {})
    prev = ticker.get('prevDay', {})
    
    return {
        'symbol': symbol.upper(),
        'price': ticker.get('lastTrade', {}).get('p'),
        'change': day.get('c', 0) - prev.get('c', 0) if day.get('c') and prev.get('c') else None,
        'change_percent': ((day.get('c', 0) / prev.get('c', 1)) - 1) * 100 if day.get('c') and prev.get('c') else None,
        'open': day.get('o'),
        'high': day.get('h'),
        'low': day.get('l'),
        'close': day.get('c'),
        'volume': day.get('v'),
        'vwap': day.get('vw'),
        'prev_close': prev.get('c'),
        'prev_volume': prev.get('v')
    }
