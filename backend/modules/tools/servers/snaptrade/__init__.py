"""
SnapTrade API - Secure brokerage account access

Connect to user's real brokerage accounts (Robinhood, TD Ameritrade, etc.)
via OAuth. No credentials stored.

Quick start:
    from servers.snaptrade.portfolio.get_holdings import get_holdings
    
    holdings = await get_holdings(user_id)
"""

from ._client import get_snaptrade_client

__all__ = ['get_snaptrade_client']

