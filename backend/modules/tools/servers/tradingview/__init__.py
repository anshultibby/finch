"""
TradingView - Technical Analysis & Charts

CAPABILITIES:
- Multi-timeframe technical analysis (1min to monthly)
- Technical indicators: RSI, MACD, moving averages, Bollinger Bands, etc
- Trend alignment analysis across timeframes (find strong trends)
- Timeframe comparison for swing vs day trading setups
- Interactive chart widgets for visualization

KEY MODULES:
- analysis.get_technical_analysis: Full TA for any symbol/timeframe
- analysis.get_trend_alignment: Check if trends align across timeframes
- analysis.get_multi_timeframe_analysis: Comprehensive MTF analysis
- analysis.compare_timeframes: Compare signals across time horizons
- charts.*: Create embeddable chart widgets

USAGE PATTERN:
Timeframes: '1m','5m','15m','30m','1h','2h','4h','1d','1W','1M'
Screener values: 'america' for US stocks, 'crypto' for crypto
Returns detailed indicator values plus buy/sell/neutral recommendations.
"""
