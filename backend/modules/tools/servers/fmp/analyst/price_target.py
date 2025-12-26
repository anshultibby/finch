"""Get analyst price targets and consensus"""
from ..api import fmp


def get_price_targets(symbol: str):
    """
    Get individual analyst price targets
    
    Args:
        symbol: Stock ticker
        
    Returns:
        list: symbol, publishedDate, analystName, analystCompany, 
              priceTarget, priceWhenPosted
    """
    return fmp('/price-target', {'symbol': symbol})


def get_price_target_consensus(symbol: str):
    """
    Get consensus price target (average of all analysts)
    
    Args:
        symbol: Stock ticker
        
    Returns:
        dict: targetConsensus, targetMedian, targetHigh, targetLow
    """
    return fmp(f'/price-target-consensus/{symbol}')
