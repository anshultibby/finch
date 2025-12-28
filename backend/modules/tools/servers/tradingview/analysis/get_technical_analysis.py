"""Get complete technical analysis for any stock/asset"""
from .._client import TradingViewClient, tradingview_request


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
        dict with:
            - summary: Overall recommendation (STRONG_BUY, BUY, NEUTRAL, SELL, STRONG_SELL)
                       with buy/sell/neutral signal counts
            - indicators: All technical indicators (RSI, MACD, ADX, CCI, etc.)
            - oscillators: Oscillator values and signals (RSI, Stochastic, CCI, Williams %R)
            - moving_averages: MA values and signals (SMA10/20/50/100/200, EMA10/20/50/100/200)
        
    Example:
        # Stock analysis
        result = get_technical_analysis('AAPL', 'NASDAQ', '1d', 'america')
        print(result['summary']['recommendation'])  # e.g., 'BUY'
        print(result['indicators']['RSI'])  # RSI value
        print(result['moving_averages'])  # All MA values
        
        # Crypto analysis  
        get_technical_analysis('BTCUSDT', 'BINANCE', '4h', 'crypto')
    """
    return TradingViewClient.get_analysis(symbol, exchange, screener, interval)
