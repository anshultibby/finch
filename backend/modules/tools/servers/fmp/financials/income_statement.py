"""Get income statement - revenue, expenses, net income"""
from ..api import fmp


def get_income_statement(symbol: str, period: str = 'annual', limit: int = 5):
    """
    Get income statement
    
    Args:
        symbol: Stock ticker
        period: 'annual' or 'quarter'
        limit: Number of periods
        
    Returns:
        list: date, revenue, costOfRevenue, grossProfit, operatingExpenses, 
              operatingIncome, netIncome, eps, epsdiluted
    """
    return fmp(f'/income-statement/{symbol}', {'period': period, 'limit': limit})
