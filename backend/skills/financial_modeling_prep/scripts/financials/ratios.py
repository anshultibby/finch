"""Get financial ratios - valuation, profitability, liquidity, leverage"""
from ..api import fmp


def get_ratios(symbol: str, period: str = 'annual', limit: int = 5):
    """
    Get financial ratios
    
    Args:
        symbol: Stock ticker
        period: 'annual' or 'quarter'
        limit: Number of periods
        
    Returns:
        list: date, priceEarningsRatio, priceToBookRatio, priceToSalesRatio,
              returnOnAssets, returnOnEquity, grossProfitMargin, 
              operatingProfitMargin, netProfitMargin, currentRatio, 
              quickRatio, debtRatio, debtEquityRatio, dividendYield
    """
    return fmp(f'/ratios/{symbol}', {'period': period, 'limit': limit})
