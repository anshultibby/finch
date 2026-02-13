"""
Dome API - Prediction Market Intelligence

CAPABILITIES:
- Search and browse Polymarket and Kalshi prediction markets
- Get market prices, probabilities, and historical candlestick data
- Track any wallet's positions, P&L, and trading activity
- Monitor trade history and order flow on markets
- Find cross-platform arbitrage opportunities (sports, politics, crypto)

KEY MODULES:
- polymarket.markets: Search markets by tags (crypto, politics, sports, etc)
- polymarket.prices: Current prices and historical candlesticks for charting
- polymarket.wallet: Track any wallet - positions, P&L, trading activity
- polymarket.trading: Trade history and order flow analysis
- kalshi.markets: Browse Kalshi events and markets
- matching.sports: Find matching markets across platforms for arbitrage

USAGE PATTERN:
Polymarket uses condition_id/token_id (hex strings starting with 0x).
Wallet tracking requires Ethereum addresses. Rate limited to 1 req/sec.
All functions return dict - always check for 'error' key.

NOTE: This is for DATA ONLY. For trading, use the kalshi server directly.
"""

from . import polymarket
from . import kalshi
from . import matching

__all__ = ['polymarket', 'kalshi', 'matching']
