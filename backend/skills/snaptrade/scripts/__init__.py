"""
SnapTrade - Brokerage Account Access & Trading

CAPABILITIES:
- Connect to user's real brokerage accounts (Robinhood, Schwab, Fidelity, etc)
- View holdings, positions, balances, orders, and activities
- Place and manage equity and option orders
- Get real-time quotes
- Manage connections (list, refresh, disconnect)
- Reference data (symbols, brokerages, currencies, exchanges)

KEY MODULES:
- portfolio.get_accounts: List connected brokerage accounts
- portfolio.get_holdings: Get aggregated holdings across all accounts
- portfolio.request_connection: Generate link for user to connect a broker

- account.get_balances: Get cash balances for an account
- account.get_positions: Get equity positions
- account.get_orders: Get order history
- account.get_activities: Get transaction history (buys, sells, dividends)
- account.get_holdings_detail: Get positions + balances + orders in one call
- account.get_option_holdings: Get option positions
- account.get_return_rates: Get return rates/performance

- trading.get_quotes: Get real-time quotes for symbols
- trading.place_order: Place equity order (market, limit, stop)
- trading.preview_order: Preview trade impact before placing
- trading.cancel_order: Cancel an open order
- trading.place_option_order: Place multi-leg option order

- connections.list_connections: List all brokerage connections
- connections.refresh_connection: Force refresh data from brokerage
- connections.disconnect_account: Disconnect a specific account
- connections.delete_connection: Delete entire brokerage connection

- reference.search_symbols: Search for tradeable symbols within an account
- reference.list_brokerages: List all supported brokerages
- reference.get_symbol_detail: Get details for a ticker
- reference.list_currencies: List currencies and exchange rates
- reference.list_exchanges: List stock exchanges

USAGE PATTERN:
User must first connect their brokerage via OAuth flow.
Functions are sync (except portfolio.get_holdings which is async).
Returns data from user's actual brokerage accounts.
"""

def get_snaptrade_client():
    from ._client import get_snaptrade_client as _get
    return _get()

__all__ = ['get_snaptrade_client']
