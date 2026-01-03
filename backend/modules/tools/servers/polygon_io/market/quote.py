"""
Real-time Quote Data - Last Trade, Bid/Ask, Snapshot

Functions:
    get_last_trade(symbol) - Last executed trade
    get_last_quote(symbol) - Current bid/ask spread
    get_snapshot(symbol) - Full market snapshot with price, change, volume

Example:
    from servers.polygon_io.market.quote import get_snapshot, get_last_trade
    
    # Get current market snapshot
    snapshot = get_snapshot('AAPL')
    # Returns: {'symbol': 'AAPL', 'price': 185.50, 'change': 2.30, 
    #           'change_percent': 1.25, 'volume': 12345678, ...}
    
    # Get last trade
    trade = get_last_trade('AAPL')
    # Returns: {'symbol': 'AAPL', 'price': 185.50, 'size': 100, ...}
"""
from .._client import call_polygon_api
from typing import Dict, Any, Optional


def get_last_trade(symbol: str) -> Dict[str, Any]:
    """
    Get the most recent trade for a stock.
    
    Parameters:
        symbol: str
            Stock ticker symbol (e.g., 'AAPL', 'NVDA')
    
    Returns:
        dict with keys:
            - symbol: str - Uppercase ticker
            - price: float - Trade price
            - size: int - Number of shares traded
            - exchange: int - Exchange ID where trade occurred
            - timestamp: int - Unix timestamp in nanoseconds
            - conditions: List[int] - Trade condition codes
    
    Example:
        >>> trade = get_last_trade('AAPL')
        >>> print(f"Last trade: ${trade['price']}")
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


def get_last_quote(symbol: str) -> Dict[str, Any]:
    """
    Get the current bid/ask quote (NBBO - National Best Bid/Offer).
    
    Parameters:
        symbol: str
            Stock ticker symbol (e.g., 'AAPL', 'NVDA')
    
    Returns:
        dict with keys:
            - symbol: str - Uppercase ticker
            - bid_price: float - Best bid price
            - bid_size: int - Bid size in shares
            - ask_price: float - Best ask price
            - ask_size: int - Ask size in shares
            - timestamp: int - Unix timestamp
    
    Example:
        >>> quote = get_last_quote('AAPL')
        >>> spread = quote['ask_price'] - quote['bid_price']
        >>> print(f"Spread: ${spread:.2f}")
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


def get_snapshot(symbol: str) -> Dict[str, Any]:
    """
    Get a complete market snapshot including price, change, and volume.
    
    This is the most useful function for getting current market data
    for a single stock.
    
    Parameters:
        symbol: str
            Stock ticker symbol (e.g., 'AAPL', 'NVDA')
    
    Returns:
        dict with keys:
            - symbol: str - Uppercase ticker
            - price: float - Current/last trade price
            - change: float - Dollar change from previous close
            - change_percent: float - Percent change from previous close
            - open: float - Today's opening price
            - high: float - Today's high
            - low: float - Today's low
            - close: float - Today's close/current price
            - volume: float - Today's trading volume
            - vwap: float - Volume-weighted average price
            - prev_close: float - Previous day's closing price
            - prev_volume: float - Previous day's volume
    
    Example:
        >>> snap = get_snapshot('NVDA')
        >>> print(f"{snap['symbol']}: ${snap['price']:.2f} ({snap['change_percent']:+.2f}%)")
        >>> print(f"Volume: {snap['volume']:,.0f}")
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
