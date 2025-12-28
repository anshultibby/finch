"""Check if trends are aligned across timeframes (bullish/bearish confluence)"""
from .compare_timeframes import compare_timeframes


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

