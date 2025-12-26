"""Get historical price data - OHLCV bars"""
from .._client import get_polygon_client, format_bars, polygon_request


@polygon_request
def get_historical_prices(symbol: str, from_date: str, to_date: str, timespan: str = 'day'):
    """
    Get historical OHLCV data
    
    Args:
        symbol: Stock ticker
        from_date: Start date (YYYY-MM-DD)
        to_date: End date (YYYY-MM-DD)
        timespan: 'minute', 'hour', 'day', 'week', 'month'
        
    Returns:
        list: timestamp, date, open, high, low, close, volume
    """
    client = get_polygon_client()
    aggs = client.get_aggs(
        ticker=symbol,
        multiplier=1,
        timespan=timespan,
        from_=from_date,
        to=to_date
    )
    return format_bars(aggs)
