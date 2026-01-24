"""
Polymarket API endpoints via Dome

Organized by functionality:
- markets: Search and discover markets
- prices: Real-time and historical pricing
- trading: Trade history and activity
- wallet: Wallet positions and P&L tracking
"""
from .markets import get_markets
from .prices import get_market_price, get_candlesticks
from .trading import get_trade_history
from .wallet import get_wallet, get_wallet_pnl

__all__ = [
    'get_markets',
    'get_market_price',
    'get_candlesticks',
    'get_trade_history',
    'get_wallet',
    'get_wallet_pnl',
]
