"""
Polygon.io API

High-quality market data with generous rate limits.

Quick start:
    from servers.polygon_io.market.historical_prices import get_historical_prices
    
    prices = get_historical_prices('AAPL', '2024-01-01', '2024-01-31')
"""

from .api import polygon

__all__ = ['polygon']
