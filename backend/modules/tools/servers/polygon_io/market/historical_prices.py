"""
Historical Price Data - Daily/Weekly/Monthly OHLCV Bars

Functions:
    get_historical_prices(symbol, from_date, to_date, timespan='day', multiplier=1)

Example:
    from servers.polygon_io.market.historical_prices import get_historical_prices
    
    response = get_historical_prices(
        symbol='AAPL',           # Stock ticker (required) - NOT ticker=!
        from_date='2024-01-01',  # Start date YYYY-MM-DD (required)
        to_date='2024-12-31',    # End date YYYY-MM-DD (required)
        timespan='day',          # Bar size (optional, default='day')
        multiplier=1             # Timespan multiplier (optional, default=1)
    )
    
    # ALWAYS check for errors before accessing data!
    if 'error' in response:
        print(f"Error: {response['error']}")
    else:
        # Response structure:
        # {
        #     'symbol': 'AAPL',
        #     'from': '2024-01-01',
        #     'to': '2024-12-31',
        #     'timespan': '1 day',
        #     'count': 252,
        #     'bars': [
        #         {'timestamp': 1704067200000, 'date': '2024-01-02',
        #          'open': 185.0, 'high': 186.5, 'low': 184.2, 'close': 185.8,
        #          'volume': 12345678, 'vwap': 185.5, 'trades': 123456},
        #         ...
        #     ]
        # }
        
        # Convert to DataFrame:
        import pandas as pd
        df = pd.DataFrame(response['bars'])
        df['date'] = pd.to_datetime(df['date'])
"""
from .._client import call_polygon_api, format_bars
from typing import Dict, Any, Literal


TimespanType = Literal['minute', 'hour', 'day', 'week', 'month', 'quarter', 'year']


def get_historical_prices(
    symbol: str,
    from_date: str,
    to_date: str,
    timespan: TimespanType = 'day',
    multiplier: int = 1
) -> Dict[str, Any]:
    """
    Get historical OHLCV price data.
    
    Parameters:
        symbol: str
            Stock ticker symbol (e.g., 'AAPL', 'MSFT', 'SPY')
            
        from_date: str
            Start date in format 'YYYY-MM-DD'
            
        to_date: str
            End date in format 'YYYY-MM-DD'
            
        timespan: str, default='day'
            Bar size. Options: 'minute', 'hour', 'day', 'week', 'month', 'quarter', 'year'
            
        multiplier: int, default=1
            Timespan multiplier (e.g., 5 for 5-minute bars when timespan='minute')
    
    Returns:
        dict with keys:
            - symbol: str - Uppercase ticker
            - from: str - Start date
            - to: str - End date
            - timespan: str - Bar size description (e.g., '1 day', '5 minute')
            - count: int - Number of bars
            - bars: List[dict] - OHLCV data with keys:
                - timestamp: int (Unix ms)
                - date: str - Date string
                - open, high, low, close: float - Prices
                - volume: float - Trading volume
                - vwap: float - Volume-weighted average price
                - trades: int - Number of trades
    
    Example:
        >>> # Daily prices for 2024 - ALWAYS use symbol= (not ticker=)
        >>> response = get_historical_prices(symbol='AAPL', from_date='2024-01-01', to_date='2024-12-31')
        >>> if 'error' in response:
        ...     print(f"Error: {response['error']}")
        ... else:
        ...     df = pd.DataFrame(response['bars'])  # Data is in 'bars' key!
        
        >>> # Weekly prices
        >>> response = get_historical_prices(symbol='AAPL', from_date='2024-01-01', to_date='2024-12-31', timespan='week')
        
        >>> # Hourly bars (for backtesting)
        >>> response = get_historical_prices(symbol='NVDA', from_date='2024-12-01', to_date='2024-12-31', timespan='hour')
    
    Note:
        - For intraday data (minute/hour), use get_intraday_bars() for simpler API
        - Adjusted for splits and dividends by default
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
