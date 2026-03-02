"""Get company executives and leadership team"""
from ..api import fmp


def get_executives(symbol: str):
    """
    Get company executives
    
    Args:
        symbol: Stock ticker
        
    Returns:
        list: Executives with name, title, pay, yearBorn, titleSince
    """
    return fmp(f'/key-executives/{symbol}')
