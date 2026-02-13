"""
Polygon.io - Stock Market Data

CAPABILITIES:
- Historical daily/weekly/monthly price bars for any US stock
- Intraday bars (1min to 1hour) for backtesting and analysis
- Real-time quotes with bid/ask spreads

KEY MODULES:
- market.historical_prices: Daily/weekly/monthly OHLCV bars
- market.intraday: Minute-level bars for intraday analysis
- market.quote: Real-time stock quotes

USAGE PATTERN:
All price functions use symbol= parameter. Returns dict with 'bars' key.
Always check for 'error' key before accessing data.
Timestamps are Unix milliseconds - convert with pd.to_datetime(ts, unit='ms').
"""

from .api import polygon

__all__ = ['polygon']
