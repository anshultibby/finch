"""
SnapTrade - Brokerage Account Access

CAPABILITIES:
- Connect to user's real brokerage accounts (Robinhood, TD Ameritrade, Schwab, etc)
- View holdings, positions, and account balances across all connected brokers
- OAuth-based - no credentials stored, user authorizes directly

KEY MODULES:
- portfolio.get_accounts: List connected brokerage accounts
- portfolio.get_holdings: Get holdings/positions for an account
- portfolio.request_connection: Generate link for user to connect a new broker

USAGE PATTERN:
User must first connect their brokerage via OAuth flow.
Functions are async and require user_id parameter.
Returns real portfolio data from user's actual brokerage accounts.
"""

from ._client import get_snaptrade_client

__all__ = ['get_snaptrade_client']

