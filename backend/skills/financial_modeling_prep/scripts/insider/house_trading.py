"""Get house trading - US House of Representatives stock trades (STOCK Act disclosures)"""
from ..api import fmp


def get_house_trading(symbol: str = None):
    """
    Get US House of Representatives stock trades
    
    Args:
        symbol: Stock ticker (optional)
        
    Returns:
        list: firstName, lastName, office, transactionDate, type (purchase/sale),
              assetName, amount (range like '$50,001 - $100,000'), owner
              
    Note: Trades disclosed 15-45 days after execution per STOCK Act
    """
    params = {'symbol': symbol} if symbol else None
    return fmp('/house-trading', params)
