"""Get balance sheet - assets, liabilities, equity"""
from ..api import fmp


def get_balance_sheet(symbol: str, period: str = 'annual', limit: int = 5):
    """
    Get balance sheet
    
    Args:
        symbol: Stock ticker
        period: 'annual' or 'quarter'
        limit: Number of periods
        
    Returns:
        list: date, cashAndCashEquivalents, totalCurrentAssets, totalAssets,
              totalCurrentLiabilities, longTermDebt, totalLiabilities, 
              totalStockholdersEquity, totalDebt
    """
    return fmp(f'/balance-sheet-statement/{symbol}', {'period': period, 'limit': limit})
