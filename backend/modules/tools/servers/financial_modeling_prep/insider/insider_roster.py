"""Get insider roster - officers, directors, 10%+ owners"""
from ..api import fmp


def get_insider_roster(symbol: str):
    """
    Get list of company insiders (executives, directors, 10%+ owners).
    
    Args:
        symbol: Stock ticker (e.g., 'AAPL')
        
    Returns:
        List of dicts: owner, transactionDate, typeOfOwner, securitiesOwned
    """
    return fmp('/insider-roster', {'symbol': symbol})
