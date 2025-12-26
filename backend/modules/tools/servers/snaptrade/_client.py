"""SnapTrade API Client"""
from modules.tools.clients.snaptrade import snaptrade_tools


def get_snaptrade_client():
    """
    Get SnapTrade client singleton
    
    This client manages secure OAuth connections to user brokerage accounts.
    No credentials stored - all auth handled by SnapTrade.
    """
    return snaptrade_tools

