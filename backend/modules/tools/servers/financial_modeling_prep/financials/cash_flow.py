"""Get cash flow statement - operating, investing, financing"""
from ..api import fmp


def get_cash_flow(symbol: str, period: str = 'annual', limit: int = 5):
    """
    Get cash flow statement
    
    Args:
        symbol: Stock ticker
        period: 'annual' or 'quarter'
        limit: Number of periods
        
    Returns:
        list: date, operatingCashFlow, freeCashFlow, capitalExpenditure,
              acquisitionsNet, debtRepayment, commonStockRepurchased, 
              dividendsPaid, netChangeInCash
    """
    return fmp(f'/cash-flow-statement/{symbol}', {'period': period, 'limit': limit})
