"""Multi-Timeframe Analysis - Compare trends across different intervals"""
from ..api import get_multi_timeframe_analysis


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


def get_trend_alignment(symbol: str, exchange: str = "NASDAQ"):
    """
    Check if trends are aligned across timeframes (bullish/bearish confluence)
    
    When multiple timeframes show same direction = stronger signal
    
    Args:
        symbol: Ticker
        exchange: Exchange
        
    Returns:
        dict: Trend alignment analysis across 15m, 1h, 4h, 1d
    """
    intervals = ['15m', '1h', '4h', '1d']
    analysis = compare_timeframes(symbol, exchange, intervals)
    
    if "error" in analysis:
        return analysis
    
    recommendations = analysis.get("recommendations", {})
    
    # Count bullish vs bearish signals
    bullish_count = sum(1 for rec in recommendations.values() 
                       if rec in ["BUY", "STRONG_BUY"])
    bearish_count = sum(1 for rec in recommendations.values() 
                       if rec in ["SELL", "STRONG_SELL"])
    
    # Determine alignment
    if bullish_count >= 3:
        alignment = "STRONG_BULLISH"
    elif bullish_count >= 2:
        alignment = "BULLISH"
    elif bearish_count >= 3:
        alignment = "STRONG_BEARISH"
    elif bearish_count >= 2:
        alignment = "BEARISH"
    else:
        alignment = "MIXED/NEUTRAL"
    
    return {
        "symbol": symbol,
        "alignment": alignment,
        "bullish_timeframes": bullish_count,
        "bearish_timeframes": bearish_count,
        "total_timeframes": len(intervals),
        "recommendations_by_interval": recommendations
    }

