"""Get market movers - gainers, losers, most active"""
from ..api import fmp


def get_gainers():
    """Get biggest stock gainers of the day"""
    return fmp('/stock_market/gainers')


def get_losers():
    """Get biggest stock losers of the day"""
    return fmp('/stock_market/losers')


def get_actives():
    """Get most actively traded stocks"""
    return fmp('/stock_market/actives')
