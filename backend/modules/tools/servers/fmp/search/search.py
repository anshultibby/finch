"""Search companies by name or ticker symbol"""
from ..api import fmp


def search(query: str, limit: int = 10, exchange: str = None):
    """
    Search companies
    
    Args:
        query: Search term (company name or ticker)
        limit: Number of results
        exchange: Filter by exchange (NASDAQ, NYSE, AMEX), optional
        
    Returns:
        list: symbol, name, currency, stockExchange, exchangeShortName
    """
    params = {'query': query, 'limit': limit}
    if exchange:
        params['exchange'] = exchange
    return fmp('/search', params)

