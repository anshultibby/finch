"""Universal SnapTrade API caller"""
from ._client import get_snaptrade_client


def snaptrade():
    """
    Get SnapTrade client for portfolio access
    
    Returns client that manages secure OAuth connections to user brokerages.
    """
    return get_snaptrade_client()

