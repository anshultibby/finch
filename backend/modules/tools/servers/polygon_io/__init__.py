"""
Polygon.io - Stock Market Data

CAPABILITIES:
- Historical daily/weekly/monthly price bars for any US stock
- Intraday bars (1min to 1hour) for backtesting and analysis
- Real-time quotes with bid/ask spreads

KEY MODULES:
- market.historical_prices: Daily/weekly/monthly OHLCV bars
- market.intraday: Minute-level bars (1min, 5min, 15min, 30min, 1hour)
- market.quote: Real-time stock quotes

USAGE:
  from servers.polygon_io.market.intraday import get_intraday_bars
  response = get_intraday_bars(symbol='NVDA', from_datetime='2024-12-01', 
                               to_datetime='2024-12-31', timespan='15min')
  
  # Response: {'symbol': 'NVDA', 'bars': [...], 'count': N}
  # Each bar: {timestamp, date, open, high, low, close, volume, vwap, trades}
  df = pd.DataFrame(response['bars'])
  df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

CRITICAL NOTES:
- Use symbol= parameter (NOT ticker=)
- Returns dict with 'bars' key, not a list directly
- Always check for 'error' key before accessing data
- Timestamps are Unix milliseconds - convert with pd.to_datetime(ts, unit='ms')
"""

from .api import polygon

__all__ = ['polygon']
