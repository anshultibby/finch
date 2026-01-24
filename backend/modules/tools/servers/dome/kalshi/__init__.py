"""
Kalshi API endpoints via Dome

Read-only access to Kalshi prediction markets via Dome API.
For trading, use the direct Kalshi API (servers.kalshi).
"""
from .markets import get_markets, get_market_price

__all__ = ['get_markets', 'get_market_price']
