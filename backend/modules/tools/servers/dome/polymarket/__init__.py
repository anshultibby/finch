"""
Polymarket API endpoints via Dome API

Provides access to Polymarket data through Dome API:
- markets: Search and discover markets
- prices: Real-time and historical pricing  
- trading: Trade execution history (BUY/SELL orders)
- wallet: Wallet positions, P&L, and on-chain activity
- clob_client: Direct CLOB access (alternative to Dome)

Key endpoints for copy trading:
- get_orders() / get_wallet_trades(): Get actual BUY/SELL executions
- get_wallet_activity(): Get SPLITS, MERGES, REDEEMS (not trades)
- get_positions(): Get current portfolio holdings
"""
from .markets import get_markets
from .prices import get_market_price, get_candlesticks
from .trading import get_orders, get_trade_history
from .wallet import get_wallet_info, get_positions, get_wallet_pnl, get_wallet_activity, get_wallet_trades
from .clob_client import (
    get_clob_client,
    get_markets_clob,
    get_orderbook,
    get_market_price as get_market_price_clob,
    get_user_orders,
    get_user_trades
)

__all__ = [
    # Dome API - Trade Executions (BUY/SELL)
    'get_orders',           # Get executed orders (BUY/SELL) - use for copy trading
    'get_wallet_trades',    # Get a wallet's trade executions
    'get_trade_history',    # Alias for get_orders
    
    # Dome API - Market Data
    'get_markets',
    'get_market_price',
    'get_candlesticks',
    
    # Dome API - Wallet Data
    'get_wallet_info',
    'get_positions',        # Current holdings
    'get_wallet_pnl',       # Realized P&L history
    'get_wallet_activity',  # SPLITS/MERGES/REDEEMS only (not trades)
    
    # Direct CLOB API (alternative - no Dome API key needed)
    'get_clob_client',
    'get_markets_clob',
    'get_orderbook',
    'get_market_price_clob',
    'get_user_orders',
    'get_user_trades',
]
