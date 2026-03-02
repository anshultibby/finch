"""Get earnings calendar - upcoming and historical earnings"""
from ..api import fmp


def get_earnings_calendar(from_date: str = None, to_date: str = None):
    """
    Get earnings calendar
    
    Args:
        from_date: Start date (YYYY-MM-DD), optional
        to_date: End date (YYYY-MM-DD), optional
        If no dates: returns today's earnings
        
    Returns:
        list: date, symbol, time (bmo/amc/dmh), eps, epsEstimated, 
              revenue, revenueEstimated, fiscalDateEnding
              
    Note: actual > estimated = beat (bullish), actual < estimated = miss (bearish)
    """
    params = {}
    if from_date:
        params['from'] = from_date
    if to_date:
        params['to'] = to_date
    return fmp('/earnings_calendar', params if params else None)


def get_historical_earnings(symbol: str):
    """Get historical earnings for specific stock (actual vs estimated)"""
    return fmp(f'/historical/earning_calendar/{symbol}')
