"""Get intraday price data - minute/hour bars"""
from .._client import call_polygon_api, format_bars
from datetime import datetime, timedelta


# Timespan mapping
TIMESPANS = {
    '1min': (1, 'minute'),
    '5min': (5, 'minute'),
    '15min': (15, 'minute'),
    '30min': (30, 'minute'),
    '1hour': (1, 'hour'),
}


def get_intraday_bars(symbol: str, from_datetime: str, to_datetime: str, timespan: str = '5min'):
    """
    Get intraday OHLCV bars
    
    Args:
        symbol: Stock ticker
        from_datetime: Start (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)
        to_datetime: End (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)
        timespan: '1min', '5min', '15min', '30min', '1hour'
        
    Returns:
        dict: symbol, timespan, count, bars (timestamp, date, open, high, low, close, volume)
    """
    if timespan not in TIMESPANS:
        return {"error": f"Invalid timespan. Use: {', '.join(TIMESPANS.keys())}"}
    
    multiplier, unit = TIMESPANS[timespan]
    
    # Convert datetime strings to dates for the API
    from_date = from_datetime.split(' ')[0]
    to_date = to_datetime.split(' ')[0]
    
    endpoint = f"/v2/aggs/ticker/{symbol.upper()}/range/{multiplier}/{unit}/{from_date}/{to_date}"
    
    result = call_polygon_api(endpoint, params={
        'adjusted': 'true',
        'sort': 'asc',
        'limit': 50000
    })
    
    if 'error' in result:
        return result
    
    if result.get('resultsCount', 0) == 0:
        return {"error": f"No intraday data found for {symbol}. Note: Intraday data requires Polygon Stocks Starter plan or higher."}
    
    bars = format_bars(result.get('results', []))
    return {
        'symbol': symbol.upper(),
        'from': from_datetime,
        'to': to_datetime,
        'timespan': timespan,
        'count': len(bars),
        'bars': bars
    }


def get_today_bars(symbol: str, timespan: str = '5min'):
    """
    Get today's intraday bars
    
    Args:
        symbol: Stock ticker
        timespan: '1min', '5min', '15min', '30min', '1hour'
        
    Returns:
        dict: Today's intraday bars
    """
    now = datetime.now()
    market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    
    # If before market open, use yesterday
    if now < market_open:
        market_open -= timedelta(days=1)
    
    from_dt = market_open.strftime('%Y-%m-%d %H:%M:%S')
    to_dt = now.strftime('%Y-%m-%d %H:%M:%S')
    
    return get_intraday_bars(symbol, from_dt, to_dt, timespan)
