"""Get senate trading - US Congress stock trades (STOCK Act disclosures)"""
from ..api import fmp


def get_senate_trading(symbol: str = None):
    """
    Get US Congress stock trades
    
    Args:
        symbol: Stock ticker (optional)
        
    Returns:
        list: firstName, lastName, office, transactionDate, type (purchase/sale_partial/sale_full),
              assetName, amount (range like '$50,001 - $100,000'), owner
              
    Note: Trades disclosed 15-45 days after execution
    """
    params = {'symbol': symbol} if symbol else None
    return fmp('/senate-trading', params)
