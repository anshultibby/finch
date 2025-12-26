"""Universal TradingView API caller"""

from ._client import TradingViewClient, tradingview_request

@tradingview_request
def get_technical_analysis(
    symbol: str,
    exchange: str = "NASDAQ",
    interval: str = "1d",
    screener: str = "america"
):
    """
    Get complete technical analysis for any stock/asset
    
    Args:
        symbol: Ticker symbol (e.g., 'AAPL', 'MSFT', 'BTCUSDT')
        exchange: Exchange (NASDAQ, NYSE, AMEX, BINANCE, etc)
        interval: Timeframe (1m, 5m, 15m, 30m, 1h, 2h, 4h, 1d, 1w, 1M)
        screener: Market type (america for stocks, crypto for crypto)
        
    Returns:
        dict: Technical analysis with indicators, summary, recommendation
        
    Example:
        # Stock analysis
        get_technical_analysis('AAPL', 'NASDAQ', '1d', 'america')
        
        # Crypto analysis  
        get_technical_analysis('BTCUSDT', 'BINANCE', '4h', 'crypto')
    """
    return TradingViewClient.get_analysis(symbol, exchange, screener, interval)


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

