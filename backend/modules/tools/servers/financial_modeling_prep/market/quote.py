"""
Stock Quote Snapshot - Daily Summary with Fundamentals

Functions:
    get_quote_snapshot(symbol) - Get quote with price, PE, market cap, etc.

Example:
    from servers.financial_modeling_prep.market.quote import get_quote_snapshot
    
    # Single stock
    quote = get_quote_snapshot('AAPL')
    # Returns: [{'symbol': 'AAPL', 'name': 'Apple Inc.', 'price': 185.50,
    #            'change': 2.30, 'changesPercentage': 1.25, 'marketCap': 2850000000000,
    #            'pe': 28.5, 'eps': 6.51, 'volume': 45678901, ...}]
    
    # Multiple stocks (comma-separated)
    quotes = get_quote_snapshot('AAPL,MSFT,GOOGL')
    # Returns: List of quote dicts

Note:
    - Returns a LIST even for single stock (use quote[0] to access)
    - For real-time tick data, use polygon_io.market.quote instead
    - Best for: daily snapshots, fundamentals (PE, market cap, EPS)
"""
from ..api import fmp
from typing import List, Dict, Any, Union


def get_quote_snapshot(symbol: str) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Get stock quote snapshot with fundamentals.
    
    Parameters:
        symbol: str
            Stock ticker symbol (e.g., 'AAPL')
            Can be comma-separated for multiple: 'AAPL,MSFT,GOOGL'
    
    Returns:
        List of dicts (even for single stock!), each with keys:
            - symbol: str - Ticker symbol
            - name: str - Company name
            - price: float - Current price
            - change: float - Dollar change
            - changesPercentage: float - Percent change
            - dayLow: float - Day's low price
            - dayHigh: float - Day's high price
            - yearLow: float - 52-week low
            - yearHigh: float - 52-week high
            - volume: int - Trading volume
            - avgVolume: int - Average volume
            - marketCap: int - Market capitalization
            - pe: float - Price-to-earnings ratio
            - eps: float - Earnings per share
            - open: float - Opening price
            - previousClose: float - Previous close
            - exchange: str - Exchange name
    
    Example:
        >>> quotes = get_quote_snapshot('NVDA')
        >>> quote = quotes[0]  # Access first (only) result
        >>> print(f"{quote['symbol']}: ${quote['price']:.2f}")
        >>> print(f"Market Cap: ${quote['marketCap']:,.0f}")
        >>> print(f"P/E: {quote['pe']:.1f}")
        
        >>> # Multiple stocks
        >>> quotes = get_quote_snapshot('AAPL,MSFT,GOOGL')
        >>> for q in quotes:
        ...     print(f"{q['symbol']}: ${q['price']:.2f}")
    
    Note:
        - Always returns a LIST, even for single stock
        - Use polygon_io.market.quote.get_snapshot() for real-time data
        - This is better for fundamentals (PE, market cap, EPS)
    """
    return fmp(f'/quote/{symbol}')
