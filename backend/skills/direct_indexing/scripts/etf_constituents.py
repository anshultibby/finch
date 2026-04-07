"""Fetch ETF holdings/constituents with weights from FMP"""
from skills.financial_modeling_prep.scripts.api import fmp
from typing import List, Dict, Any


def get_etf_holdings(etf_symbol: str) -> List[Dict[str, Any]]:
    """
    Get the individual stock holdings of an ETF with their weights.

    Args:
        etf_symbol: ETF ticker (e.g., 'SPY', 'QQQ', 'VTI')

    Returns:
        List of dicts, each with:
            asset        – stock ticker
            name         – company name
            weightPercentage – portfolio weight (0–100)
            sharesNumber – shares held by ETF
            marketValue  – market value held by ETF

    Example:
        holdings = get_etf_holdings('SPY')
        # [{'asset': 'AAPL', 'weightPercentage': 7.12, ...}, ...]
    """
    result = fmp(f'/etf-holder/{etf_symbol}')
    if isinstance(result, dict) and 'error' in result:
        return result
    return result or []


def get_etf_info(etf_symbol: str) -> Dict[str, Any]:
    """
    Get ETF profile / basic info.

    Args:
        etf_symbol: ETF ticker

    Returns:
        dict with symbol, name, description, nav, expenseRatio, etc.
    """
    result = fmp(f'/profile/{etf_symbol}')
    if isinstance(result, list) and result:
        return result[0]
    return result or {}
