"""Technical Indicators - RSI, MACD, Bollinger Bands, etc"""
from ..api import get_technical_analysis


def get_indicators(symbol: str, exchange: str = "NASDAQ", interval: str = "1d"):
    """
    Get all technical indicators for a symbol
    
    Includes: RSI, MACD, Stochastic, ADX, CCI, Williams %R, etc.
    
    Args:
        symbol: Ticker (e.g., 'AAPL')
        exchange: Exchange (NASDAQ, NYSE, etc)
        interval: Timeframe (1m, 5m, 15m, 30m, 1h, 2h, 4h, 1d, 1w, 1M)
        
    Returns:
        dict: All available technical indicators with current values
    """
    analysis = get_technical_analysis(symbol, exchange, interval)
    if "error" in analysis:
        return analysis
    return {
        "symbol": symbol,
        "interval": interval,
        "indicators": analysis.get("indicators", {})
    }


def get_oscillators(symbol: str, exchange: str = "NASDAQ", interval: str = "1d"):
    """
    Get oscillator indicators (RSI, Stochastic, CCI, etc)
    
    Oscillators help identify overbought/oversold conditions
    
    Args:
        symbol: Ticker
        exchange: Exchange
        interval: Timeframe
        
    Returns:
        dict: Oscillator values and signals
    """
    analysis = get_technical_analysis(symbol, exchange, interval)
    if "error" in analysis:
        return analysis
    return {
        "symbol": symbol,
        "interval": interval,
        "oscillators": analysis.get("oscillators", {})
    }


def get_moving_averages(symbol: str, exchange: str = "NASDAQ", interval: str = "1d"):
    """
    Get moving average indicators (SMA, EMA)
    
    Includes: SMA10, SMA20, SMA50, SMA100, SMA200, EMA10, EMA20, etc.
    
    Args:
        symbol: Ticker
        exchange: Exchange
        interval: Timeframe
        
    Returns:
        dict: Moving average values and signals
    """
    analysis = get_technical_analysis(symbol, exchange, interval)
    if "error" in analysis:
        return analysis
    return {
        "symbol": symbol,
        "interval": interval,
        "moving_averages": analysis.get("moving_averages", {})
    }


def get_recommendation(symbol: str, exchange: str = "NASDAQ", interval: str = "1d"):
    """
    Get overall buy/sell/neutral recommendation
    
    Based on analysis of all indicators and moving averages
    
    Args:
        symbol: Ticker
        exchange: Exchange
        interval: Timeframe
        
    Returns:
        dict: Summary recommendation (STRONG_BUY, BUY, NEUTRAL, SELL, STRONG_SELL)
    """
    analysis = get_technical_analysis(symbol, exchange, interval)
    if "error" in analysis:
        return analysis
    return {
        "symbol": symbol,
        "interval": interval,
        "summary": analysis.get("summary", {})
    }

