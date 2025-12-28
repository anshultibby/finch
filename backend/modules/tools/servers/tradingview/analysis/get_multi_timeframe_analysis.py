"""Analyze across multiple timeframes for comprehensive view"""
from .._client import TradingViewClient, tradingview_request


@tradingview_request
def get_multi_timeframe_analysis(
    symbol: str,
    exchange: str = "NASDAQ",
    screener: str = "america",
    intervals: list = None
):
    """
    Analyze across multiple timeframes for comprehensive view
    
    Args:
        symbol: Ticker symbol
        exchange: Exchange name
        screener: Market type
        intervals: List of intervals (default: ['15m', '1h', '4h', '1d'])
        
    Returns:
        dict: Analysis for each timeframe
        
    Example:
        get_multi_timeframe_analysis('TSLA', intervals=['1h', '4h', '1d'])
    """
    return TradingViewClient.get_multiple_intervals(symbol, exchange, screener, intervals)

