"""
Intraday Price Data - Minute/Hour OHLCV Bars

Functions:
    get_intraday_bars(symbol, from_datetime, to_datetime, timespan='5min')
    get_today_bars(symbol, timespan='5min')

Example:
    from servers.polygon_io.market.intraday import get_intraday_bars
    
    response = get_intraday_bars(
        symbol='NVDA',           # Stock ticker (required) - NOT ticker=!
        from_datetime='2024-01-01',  # Start date YYYY-MM-DD (required)
        to_datetime='2024-01-31',    # End date YYYY-MM-DD (required)
        timespan='15min'         # Bar size (optional, default='5min')
    )
    
    # ALWAYS check for errors before accessing data!
    if 'error' in response:
        print(f"Error: {response['error']}")
    else:
        # Response structure:
        # {
        #     'symbol': 'NVDA',
        #     'from': '2024-01-01',
        #     'to': '2024-01-31',
        #     'timespan': '15min',
        #     'count': 1234,
        #     'bars': [
        #         {'timestamp': 1704067200000, 'date': '2024-01-01 09:30:00',
        #          'open': 495.0, 'high': 496.5, 'low': 494.2, 'close': 495.8,
        #          'volume': 123456, 'vwap': 495.5, 'trades': 1234},
        #         ...
        #     ]
        # }
        
        # Convert to DataFrame:
        import pandas as pd
        df = pd.DataFrame(response['bars'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
"""
from .._client import call_polygon_api, format_bars
from datetime import datetime, timedelta
from typing import Dict, Any, List, Union, Literal


# Valid timespan options
TIMESPANS = {
    '1min': (1, 'minute'),
    '5min': (5, 'minute'),
    '15min': (15, 'minute'),
    '30min': (30, 'minute'),
    '1hour': (1, 'hour'),
}

TimespanType = Literal['1min', '5min', '15min', '30min', '1hour']


def get_intraday_bars(
    symbol: str,
    from_datetime: str,
    to_datetime: str,
    timespan: TimespanType = '5min'
) -> Dict[str, Any]:
    """
    Get intraday OHLCV bars for a stock.
    
    Parameters:
        symbol: str
            Stock ticker symbol (e.g., 'NVDA', 'AAPL', 'SPY')
            
        from_datetime: str
            Start date in format 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS'
            
        to_datetime: str
            End date in format 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS'
            
        timespan: str, default='5min'
            Bar size. Options: '1min', '5min', '15min', '30min', '1hour'
    
    Returns:
        dict with keys:
            - symbol: str - Uppercase ticker
            - from: str - Start date
            - to: str - End date  
            - timespan: str - Bar size
            - count: int - Number of bars
            - bars: List[dict] - OHLCV data with keys:
                - timestamp: int (Unix ms) - Use pd.to_datetime(df['timestamp'], unit='ms')
                - date: str - Human-readable datetime
                - open, high, low, close: float - Prices
                - volume: float - Trading volume
                - vwap: float - Volume-weighted average price
                - trades: int - Number of trades
    
    Example:
        >>> # ALWAYS use symbol= (not ticker=), and check for errors!
        >>> response = get_intraday_bars(symbol='NVDA', from_datetime='2024-12-01', to_datetime='2024-12-31', timespan='15min')
        >>> if 'error' in response:
        ...     print(f"Error: {response['error']}")
        ... else:
        ...     df = pd.DataFrame(response['bars'])  # Data is in 'bars' key!
        ...     df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        ...     print(f"Got {response['count']} bars")
    
    Note:
        - Intraday data requires Polygon Stocks Starter plan or higher
        - For daily/weekly data, use get_historical_prices() instead
    """
    if timespan not in TIMESPANS:
        valid_options = ', '.join(TIMESPANS.keys())
        return {"error": f"Invalid timespan '{timespan}'. Valid options: {valid_options}"}
    
    multiplier, unit = TIMESPANS[timespan]
    
    # Extract just the date part for the API
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
        return {
            "error": f"No intraday data found for {symbol}. "
                     "Note: Intraday data requires Polygon Stocks Starter plan or higher."
        }
    
    bars = format_bars(result.get('results', []))
    return {
        'symbol': symbol.upper(),
        'from': from_datetime,
        'to': to_datetime,
        'timespan': timespan,
        'count': len(bars),
        'bars': bars
    }


def get_today_bars(
    symbol: str,
    timespan: TimespanType = '5min'
) -> Dict[str, Any]:
    """
    Get today's intraday bars (from market open to now).
    
    Parameters:
        symbol: str
            Stock ticker symbol (e.g., 'NVDA', 'AAPL')
            
        timespan: str, default='5min'
            Bar size. Options: '1min', '5min', '15min', '30min', '1hour'
    
    Returns:
        Same structure as get_intraday_bars()
    
    Example:
        >>> response = get_today_bars('AAPL', '15min')
        >>> df = pd.DataFrame(response['bars'])
    """
    now = datetime.now()
    market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    
    # If before market open, use yesterday
    if now < market_open:
        market_open -= timedelta(days=1)
    
    from_dt = market_open.strftime('%Y-%m-%d %H:%M:%S')
    to_dt = now.strftime('%Y-%m-%d %H:%M:%S')
    
    return get_intraday_bars(symbol, from_dt, to_dt, timespan)
