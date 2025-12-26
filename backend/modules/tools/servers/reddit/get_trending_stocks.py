"""
Get trending stocks from Reddit via ApeWisdom API

Returns stocks with high mention counts across Reddit communities.
"""

def get_trending_stocks(limit: int = 20):
    """
    Get trending stocks on Reddit
    
    Args:
        limit: Number of stocks to return (default: 20)
        
    Returns:
        list: Trending stocks, each with:
            - ticker: Stock symbol
            - mentions: Number of mentions
            - rank: Trending rank
            - upvotes: Total upvotes
            
    Example:
        >>> stocks = get_trending_stocks(limit=10)
        >>> for stock in stocks:
        ...     print(f"{stock['rank']}. {stock['ticker']}: {stock['mentions']} mentions")
        1. GME: 1,234 mentions
        2. AMC: 987 mentions
    """
    from ._client import call_apewisdom_api
    
    data = call_apewisdom_api('/filter/all-stocks', {'page': 1})
    
    if 'error' in data:
        return data
    
    results = data.get('results', [])[:limit]
    return results

