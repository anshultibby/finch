"""
Polygon.io API

High-quality market data with generous rate limits.

Quick start:
    from servers.polygon_io.market.historical_prices import get_historical_prices
    
    # IMPORTANT: Use symbol= (not ticker=), and check for errors!
    response = get_historical_prices(symbol='AAPL', from_date='2024-01-01', to_date='2024-01-31')
    if 'error' in response:
        print(f"Error: {response['error']}")
    else:
        bars = response['bars']  # Data is in 'bars' key, not the response directly
"""

from .api import polygon

__all__ = ['polygon']
