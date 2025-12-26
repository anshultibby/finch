"""Get intraday price data - minute/hour bars"""
from .._client import get_polygon_client, format_bars, polygon_request
from datetime import datetime, timedelta


# Timespan mapping
TIMESPANS = {
    '1min': (1, 'minute'),
    '5min': (5, 'minute'),
    '15min': (15, 'minute'),
    '30min': (30, 'minute'),
    '1hour': (1, 'hour'),
}


@polygon_request
def get_intraday_bars(symbol: str, from_datetime: str, to_datetime: str, timespan: str = '5min'):
    """
    Get intraday OHLCV bars
    
    Args:
        symbol: Stock ticker
        from_datetime: Start (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)
        to_datetime: End (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)
        timespan: '1min', '5min', '15min', '30min', '1hour'
        
    Returns:
        list: timestamp, date, open, high, low, close, volume
    """
    if timespan not in TIMESPANS:
        return {"error": f"Invalid timespan. Use: {', '.join(TIMESPANS.keys())}"}
    
    multiplier, unit = TIMESPANS[timespan]
    client = get_polygon_client()
    
    aggs = client.get_aggs(
        ticker=symbol,
        multiplier=multiplier,
        timespan=unit,
        from_=from_datetime,
        to=to_datetime
    )
    return format_bars(aggs)


@polygon_request
def get_today_bars(symbol: str, timespan: str = '5min'):
    """
    Get today's intraday bars
    
    Args:
        symbol: Stock ticker
        timespan: '1min', '5min', '15min', '30min', '1hour'
        
    Returns:
        list: Today's intraday bars
    """
    now = datetime.now()
    market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    
    # If before market open, use yesterday
    if now < market_open:
        market_open -= timedelta(days=1)
    
    from_dt = market_open.strftime('%Y-%m-%d %H:%M:%S')
    to_dt = now.strftime('%Y-%m-%d %H:%M:%S')
    
    return get_intraday_bars(symbol, from_dt, to_dt, timespan)
