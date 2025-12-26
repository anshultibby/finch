"""Get company profile - name, sector, market cap, description, CEO, website"""
from ..api import fmp


def get_profile(symbol: str):
    """
    Get company profile
    
    Args:
        symbol: Stock ticker (e.g., 'AAPL')
        
    Returns:
        dict: companyName, mktCap, sector, industry, description, ceo, website, exchange, ipoDate
    """
    return fmp(f'/profile/{symbol}')
