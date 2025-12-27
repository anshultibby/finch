"""Get insider trading - corporate insider buy/sell transactions"""
from ..api import fmp


def get_insider_trading(symbol: str = None, limit: int = 100):
    """
    Get insider trading transactions
    
    Args:
        symbol: Stock ticker (optional, leave empty for all stocks)
        limit: Number of trades
        
    Returns:
        list: symbol, filingDate, transactionDate, reportingName, 
              transactionType (P-Purchase=buy, S-Sale=sell), 
              securitiesTransacted, price, securitiesOwned
    """
    params = {'limit': limit}
    if symbol:
        params['symbol'] = symbol
    return fmp('/insider-trading', params)
