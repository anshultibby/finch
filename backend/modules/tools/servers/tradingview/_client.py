"""TradingView API Client - Technical Analysis & Chart Data"""
from tradingview_ta import TA_Handler, Interval
from typing import Dict, Any, Optional, List


def tradingview_request(func):
    """Decorator to handle TradingView API errors uniformly"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            return {"error": str(e)}
    return wrapper


class TradingViewClient:
    """Client for TradingView technical analysis"""
    
    # Supported exchanges
    EXCHANGES = {
        "NASDAQ": "NASDAQ",
        "NYSE": "NYSE", 
        "AMEX": "AMEX",
        "BINANCE": "BINANCE",  # For crypto if needed
        "KUCOIN": "KUCOIN"
    }
    
    # Interval mapping
    INTERVALS = {
        "1m": Interval.INTERVAL_1_MINUTE,
        "5m": Interval.INTERVAL_5_MINUTES,
        "15m": Interval.INTERVAL_15_MINUTES,
        "30m": Interval.INTERVAL_30_MINUTES,
        "1h": Interval.INTERVAL_1_HOUR,
        "2h": Interval.INTERVAL_2_HOURS,
        "4h": Interval.INTERVAL_4_HOURS,
        "1d": Interval.INTERVAL_1_DAY,
        "1w": Interval.INTERVAL_1_WEEK,
        "1M": Interval.INTERVAL_1_MONTH
    }
    
    @staticmethod
    def get_analysis(
        symbol: str,
        exchange: str = "NASDAQ",
        screener: str = "america",
        interval: str = "1d"
    ) -> Dict[str, Any]:
        """
        Get complete technical analysis for a symbol
        
        Args:
            symbol: Ticker symbol (e.g., 'AAPL', 'TSLA')
            exchange: Exchange name (default: NASDAQ)
            screener: Market screener (america/crypto)
            interval: Time interval (1m, 5m, 15m, 30m, 1h, 2h, 4h, 1d, 1w, 1M)
            
        Returns:
            dict: Complete technical analysis including:
                - summary: Overall recommendation (BUY/SELL/NEUTRAL)
                - indicators: All technical indicators (RSI, MACD, MA, etc)
                - oscillators: Oscillator indicators
                - moving_averages: MA indicators
        """
        interval_obj = TradingViewClient.INTERVALS.get(interval, Interval.INTERVAL_1_DAY)
        
        handler = TA_Handler(
            symbol=symbol,
            exchange=exchange,
            screener=screener,
            interval=interval_obj,
            timeout=10
        )
        
        analysis = handler.get_analysis()
        
        return {
            "symbol": symbol,
            "exchange": exchange,
            "interval": interval,
            "summary": {
                "recommendation": analysis.summary.get("RECOMMENDATION"),
                "buy": analysis.summary.get("BUY"),
                "sell": analysis.summary.get("SELL"),
                "neutral": analysis.summary.get("NEUTRAL")
            },
            "indicators": analysis.indicators,
            "oscillators": analysis.oscillators,
            "moving_averages": analysis.moving_averages
        }
    
    @staticmethod
    def get_multiple_intervals(
        symbol: str,
        exchange: str = "NASDAQ",
        screener: str = "america",
        intervals: List[str] = None
    ) -> Dict[str, Any]:
        """
        Get analysis across multiple timeframes for better perspective
        
        Args:
            symbol: Ticker symbol
            exchange: Exchange name
            screener: Market screener
            intervals: List of intervals to analyze (default: ['15m', '1h', '4h', '1d'])
            
        Returns:
            dict: Analysis for each interval
        """
        if intervals is None:
            intervals = ['15m', '1h', '4h', '1d']
        
        results = {}
        for interval in intervals:
            try:
                results[interval] = TradingViewClient.get_analysis(
                    symbol=symbol,
                    exchange=exchange,
                    screener=screener,
                    interval=interval
                )
            except Exception as e:
                results[interval] = {"error": str(e)}
        
        return {
            "symbol": symbol,
            "exchange": exchange,
            "intervals": results
        }

