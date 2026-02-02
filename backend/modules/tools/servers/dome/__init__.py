"""
Dome API - Prediction Market Data

Access to Polymarket and Kalshi prediction market data via Dome API.
Includes automatic rate limiting (1 request per second for free tier).

Modules:
- polymarket: Polymarket markets, prices, positions, and trading data
- kalshi: Kalshi markets and pricing
- matching: Cross-platform market matching for arbitrage opportunities
"""

# Import submodules for easier access
from . import polymarket
from . import kalshi
from . import matching

__all__ = ['polymarket', 'kalshi', 'matching']
