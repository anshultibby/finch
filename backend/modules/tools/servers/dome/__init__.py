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

USAGE:
  from servers.dome.polymarket.wallet import get_positions, get_wallet_activity, get_wallet_pnl
  from servers.dome.polymarket.markets import get_markets
  
  # Track wallet positions
  positions = get_positions("0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb")
  for pos in positions['positions']:
      print(f"{pos['title']}: {pos['shares_normalized']} {pos['label']}")
  
  # Search markets
  markets = get_markets(search="bitcoin", status="open", limit=20)

CRITICAL NOTES:
- Polymarket uses condition_id/token_id (hex strings starting with 0x)
- Wallet tracking requires Ethereum addresses
- Rate limited to 1 req/sec - always check for 'error' key
- This is for DATA ONLY. For trading, use the kalshi server directly.
"""

from . import polymarket
from . import kalshi
from . import matching

__all__ = ['polymarket', 'kalshi', 'matching']
