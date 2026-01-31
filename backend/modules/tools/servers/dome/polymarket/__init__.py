"""
Polymarket API endpoints

Provides two access methods:
1. Direct CLOB API (via py-clob-client) - Recommended, no API key needed for read-only
2. Dome API fallback (for features not in CLOB client)

Organized by functionality:
- markets: Search and discover markets
- prices: Real-time and historical pricing
- trading: Trade history and activity
- wallet: Wallet positions and P&L tracking
- clob_client: Direct CLOB access (NEW - bypasses Dome API 403 errors)
"""
from .markets import get_markets
from .prices import get_market_price, get_candlesticks
from .trading import get_trade_history
from .wallet import get_wallet_info, get_positions, get_wallet_pnl, get_wallet_activity
from .clob_client import (
    get_clob_client,
    get_markets_clob,
    get_orderbook,
    get_market_price as get_market_price_clob,
    get_user_orders,
    get_user_trades
)

__all__ = [
    # Dome API (fallback)
    'get_markets',
    'get_market_price',
    'get_candlesticks',
    'get_trade_history',
    'get_wallet_info',
    'get_positions',
    'get_wallet_pnl',
    'get_wallet_activity',
    
    # Direct CLOB API (recommended - no 403 errors)
    'get_clob_client',
    'get_markets_clob',
    'get_orderbook',
    'get_market_price_clob',
    'get_user_orders',
    'get_user_trades',
]
