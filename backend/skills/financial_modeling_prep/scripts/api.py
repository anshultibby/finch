"""Universal FMP API caller"""

from ._client import call_fmp_api, call_fmp_stable_api

def fmp(endpoint: str, params: dict = None):
    """
    Call any FMP API endpoint
    
    Args:
        endpoint: API path (e.g., '/profile/AAPL')
        params: Optional params (e.g., {'period': 'annual', 'limit': 5})
        
    Returns:
        dict or list: API response
        
    Examples:
        fmp('/profile/AAPL')
        fmp('/income-statement/AAPL', {'period': 'annual', 'limit': 5})
        fmp('/quote/AAPL,MSFT,GOOGL')  # Batch
    """
    return call_fmp_api(endpoint, params)


def fmp_stable(endpoint: str, params: dict = None):
    """
    Call FMP Stable API endpoint (uses /stable/ base)
    
    Args:
        endpoint: API path (e.g., '/institutional-ownership/symbol-positions-summary')
        params: Optional params (e.g., {'symbol': 'AAPL', 'year': 2024})
        
    Returns:
        dict or list: API response
    """
    return call_fmp_stable_api(endpoint, params)
