"""Compare trends across different intervals"""
from .get_multi_timeframe_analysis import get_multi_timeframe_analysis


def compare_timeframes(
    symbol: str, 
    exchange: str = "NASDAQ",
    intervals: list = None
):
    """
    Analyze a symbol across multiple timeframes
    
    Helps identify:
    - Short-term vs long-term trends
    - Entry/exit points across timeframes
    - Trend alignment or divergence
    
    Args:
        symbol: Ticker (e.g., 'AAPL', 'TSLA')
        exchange: Exchange (NASDAQ, NYSE, etc)
        intervals: List of intervals to compare (default: ['15m', '1h', '4h', '1d'])
        
    Returns:
        dict: Analysis for each timeframe with recommendations
        
    Example Usage:
        # Compare intraday to daily
        compare_timeframes('AAPL', intervals=['15m', '1h', '4h', '1d'])
        
        # Quick scalping view
        compare_timeframes('TSLA', intervals=['1m', '5m', '15m'])
        
        # Swing trading view
        compare_timeframes('MSFT', intervals=['4h', '1d', '1w'])
    """
    if intervals is None:
        intervals = ['15m', '1h', '4h', '1d']
    
    result = get_multi_timeframe_analysis(symbol, exchange, "america", intervals)
    
    if "error" in result:
        return result
    
    # Extract recommendations for easy comparison
    recommendations = {}
    for interval, data in result.get("intervals", {}).items():
        if "error" not in data:
            recommendations[interval] = data.get("summary", {}).get("recommendation")
    
    return {
        "symbol": symbol,
        "exchange": exchange,
        "recommendations": recommendations,
        "full_analysis": result.get("intervals", {})
    }

