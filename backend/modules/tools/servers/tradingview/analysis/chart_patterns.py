"""Chart Pattern Detection - Using technical indicators as proxy"""
from ..api import get_technical_analysis


def detect_bollinger_squeeze(symbol: str, exchange: str = "NASDAQ", interval: str = "1d"):
    """
    Detect Bollinger Band squeeze (low volatility before breakout)
    
    A squeeze occurs when bands are tight (BBW is low), indicating
    potential upcoming volatility and price movement.
    
    Args:
        symbol: Ticker
        exchange: Exchange
        interval: Timeframe
        
    Returns:
        dict: Bollinger Band status and squeeze indication
    """
    analysis = get_technical_analysis(symbol, exchange, interval)
    if "error" in analysis:
        return analysis
    
    indicators = analysis.get("indicators", {})
    
    # Get Bollinger Band values
    bb_upper = indicators.get("BB.upper")
    bb_lower = indicators.get("BB.lower")
    bb_middle = indicators.get("BB.middle")
    close = indicators.get("close")
    
    if None in [bb_upper, bb_lower, bb_middle, close]:
        return {"error": "Bollinger Band data not available"}
    
    # Calculate band width (normalized)
    band_width = (bb_upper - bb_lower) / bb_middle
    
    # Determine squeeze (band width < 0.05 = tight squeeze)
    is_squeeze = band_width < 0.05
    squeeze_strength = "TIGHT" if band_width < 0.03 else "MODERATE" if is_squeeze else "NORMAL"
    
    # Determine position in bands
    band_range = bb_upper - bb_lower
    position_pct = ((close - bb_lower) / band_range) * 100 if band_range > 0 else 50
    
    if close > bb_upper:
        position = "ABOVE_UPPER_BAND"
    elif close < bb_lower:
        position = "BELOW_LOWER_BAND"
    elif position_pct > 60:
        position = "UPPER_BAND"
    elif position_pct < 40:
        position = "LOWER_BAND"
    else:
        position = "MIDDLE"
    
    return {
        "symbol": symbol,
        "interval": interval,
        "is_squeeze": is_squeeze,
        "squeeze_strength": squeeze_strength,
        "band_width": round(band_width, 4),
        "price_position": position,
        "price_position_pct": round(position_pct, 2),
        "bollinger_bands": {
            "upper": bb_upper,
            "middle": bb_middle,
            "lower": bb_lower,
            "current_price": close
        }
    }


def check_rsi_divergence(symbol: str, exchange: str = "NASDAQ", interval: str = "1d"):
    """
    Check RSI for overbought/oversold conditions
    
    RSI > 70 = Overbought (potential reversal down)
    RSI < 30 = Oversold (potential reversal up)
    
    Args:
        symbol: Ticker
        exchange: Exchange
        interval: Timeframe
        
    Returns:
        dict: RSI value and interpretation
    """
    analysis = get_technical_analysis(symbol, exchange, interval)
    if "error" in analysis:
        return analysis
    
    indicators = analysis.get("indicators", {})
    rsi = indicators.get("RSI")
    
    if rsi is None:
        return {"error": "RSI data not available"}
    
    # Interpret RSI
    if rsi > 70:
        condition = "OVERBOUGHT"
        signal = "Potential sell signal - consider taking profits"
    elif rsi < 30:
        condition = "OVERSOLD"
        signal = "Potential buy signal - consider entry"
    elif rsi > 60:
        condition = "STRONG"
        signal = "Bullish momentum"
    elif rsi < 40:
        condition = "WEAK"
        signal = "Bearish momentum"
    else:
        condition = "NEUTRAL"
        signal = "No extreme condition"
    
    return {
        "symbol": symbol,
        "interval": interval,
        "rsi": round(rsi, 2),
        "condition": condition,
        "signal": signal
    }


def check_macd_crossover(symbol: str, exchange: str = "NASDAQ", interval: str = "1d"):
    """
    Check MACD for bullish/bearish crossovers
    
    MACD > Signal = Bullish
    MACD < Signal = Bearish
    
    Args:
        symbol: Ticker
        exchange: Exchange
        interval: Timeframe
        
    Returns:
        dict: MACD values and crossover status
    """
    analysis = get_technical_analysis(symbol, exchange, interval)
    if "error" in analysis:
        return analysis
    
    indicators = analysis.get("indicators", {})
    macd = indicators.get("MACD.macd")
    signal = indicators.get("MACD.signal")
    
    if None in [macd, signal]:
        return {"error": "MACD data not available"}
    
    # Determine crossover
    if macd > signal:
        crossover = "BULLISH"
        interpretation = "MACD above signal line - uptrend"
    else:
        crossover = "BEARISH"
        interpretation = "MACD below signal line - downtrend"
    
    return {
        "symbol": symbol,
        "interval": interval,
        "macd": round(macd, 4),
        "signal": round(signal, 4),
        "crossover": crossover,
        "interpretation": interpretation
    }

