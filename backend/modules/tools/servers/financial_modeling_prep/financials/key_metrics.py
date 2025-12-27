"""Get key metrics - market cap, PE, EPS, free cash flow per share"""
from ..api import fmp


def get_key_metrics(symbol: str, period: str = 'annual', limit: int = 5):
    """
    Get key metrics
    
    Args:
        symbol: Stock ticker
        period: 'annual' or 'quarter'
        limit: Number of periods
        
    Returns:
        list: date, marketCap, enterpriseValue, peRatio, pegRatio, 
              revenuePerShare, netIncomePerShare, operatingCashFlowPerShare,
              freeCashFlowPerShare, debtToEquity, dividendYield
    """
    return fmp(f'/key-metrics/{symbol}', {'period': period, 'limit': limit})


def get_key_metrics_ttm(symbol: str):
    """Get trailing twelve months key metrics (most recent)"""
    return fmp(f'/key-metrics-ttm/{symbol}')
