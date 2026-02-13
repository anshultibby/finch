"""
Kalshi - Prediction Market Trading (Authenticated)

CAPABILITIES:
- View account balance and portfolio positions
- Browse open prediction market events (politics, economics, sports, crypto)
- Get detailed market info with current prices and order books
- Place orders (buy/sell YES or NO contracts)
- Manage open orders (view, cancel)

KEY MODULES:
- portfolio: Get balance, positions, and full portfolio state
- markets: Browse events and get market details with pricing
- trading: Place orders, view orders, cancel orders

USAGE PATTERN:
Requires user's Kalshi API credentials (saved in Settings > API Keys).
Market tickers look like "KXBTC-24DEC31-T100000" (event-date-strike).
Prices are in cents (0-100). Position sizes in number of contracts.

NOTE: This is the TRADING API. For broader market data/research, use dome.kalshi.
"""

from .portfolio import get_kalshi_balance, get_kalshi_positions, get_kalshi_portfolio
from .markets import get_kalshi_events, get_kalshi_market
from .trading import place_kalshi_order, get_kalshi_orders, cancel_kalshi_order

__all__ = [
    'get_kalshi_balance',
    'get_kalshi_positions', 
    'get_kalshi_portfolio',
    'get_kalshi_events',
    'get_kalshi_market',
    'place_kalshi_order',
    'get_kalshi_orders',
    'cancel_kalshi_order',
]
