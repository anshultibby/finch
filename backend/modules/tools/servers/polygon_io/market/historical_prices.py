"""Get historical price data - OHLCV bars"""
from .._client import call_polygon_api, format_bars


def get_historical_prices(symbol: str, from_date: str, to_date: str, timespan: str = 'day', multiplier: int = 1):
    """
    Get historical OHLCV data
    
    Args:
        symbol: Stock ticker
        from_date: Start date (YYYY-MM-DD)
        to_date: End date (YYYY-MM-DD)
        timespan: 'minute', 'hour', 'day', 'week', 'month', 'quarter', 'year'
        multiplier: Size of timespan (e.g., 5 for 5-minute bars)
        
    Returns:
        list: timestamp, date, open, high, low, close, volume, vwap, trades
    """
    endpoint = f"/v2/aggs/ticker/{symbol.upper()}/range/{multiplier}/{timespan}/{from_date}/{to_date}"
    
    result = call_polygon_api(endpoint, params={
        'adjusted': 'true',
        'sort': 'asc',
        'limit': 50000
    })
    
    if 'error' in result:
        return result
    
    if result.get('resultsCount', 0) == 0:
        return {"error": f"No data found for {symbol} in the specified date range"}
    
    bars = format_bars(result.get('results', []))
    return {
        'symbol': symbol.upper(),
        'from': from_date,
        'to': to_date,
        'timespan': f"{multiplier} {timespan}",
        'count': len(bars),
        'bars': bars
    }
