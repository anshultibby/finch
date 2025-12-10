"""
Finch Runtime - Preloaded clients and utilities for code execution

This module is automatically available in all execute_code environments.
It provides direct access to API clients without needing tool calls.

Usage in execute_code:
    from finch_runtime import fmp, reddit, polygon
    
    # Fetch data directly
    data = fmp.fetch('quote', {'symbol': 'AAPL'})
    sentiment = reddit.get_trending(limit=10)
    quote = polygon.get_quote('AAPL')
"""
import os
import requests
from typing import Dict, Any, Optional, List


class FMPClient:
    """
    Direct FMP API client for code execution.
    
    All data fetching happens in code - results never flow through LLM context.
    """
    
    BASE_URL = "https://financialmodelingprep.com/api/v3"
    
    def __init__(self):
        self.api_key = os.getenv('FMP_API_KEY', '')
        if not self.api_key:
            print("⚠️ Warning: FMP_API_KEY not set in environment")
    
    def fetch(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Fetch data from any FMP endpoint.
        
        Args:
            endpoint: FMP endpoint name (e.g., 'quote', 'income-statement', 'insider-trading')
            params: Query parameters (e.g., {'symbol': 'AAPL', 'limit': 10})
        
        Returns:
            API response as dict or list
        
        Examples:
            # Get quote
            quote = fmp.fetch('quote', {'symbol': 'AAPL'})
            
            # Get insider trading
            trades = fmp.fetch('insider-trading', {'symbol': 'AAPL', 'limit': 100})
            
            # Get income statement
            income = fmp.fetch('income-statement', {'symbol': 'AAPL', 'period': 'annual'})
        """
        params = params or {}
        
        # Determine if symbol goes in path (most endpoints)
        symbol = params.pop('symbol', None)
        
        # Build URL
        if symbol and endpoint in ['quote', 'profile', 'income-statement', 'balance-sheet-statement', 
                                    'cash-flow-statement', 'key-metrics', 'ratios', 'financial-growth',
                                    'historical-price-full', 'analyst-estimates']:
            url = f"{self.BASE_URL}/{endpoint}/{symbol}"
        else:
            url = f"{self.BASE_URL}/{endpoint}"
        
        # Add API key
        params['apikey'] = self.api_key
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"❌ FMP API error: {e}")
            return None
    
    def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get real-time quote for a symbol"""
        result = self.fetch('quote', {'symbol': symbol})
        return result[0] if result and isinstance(result, list) else result
    
    def get_income_statement(self, symbol: str, period: str = 'annual', limit: int = 5) -> List[Dict[str, Any]]:
        """Get income statement"""
        return self.fetch('income-statement', {'symbol': symbol, 'period': period, 'limit': limit}) or []
    
    def get_balance_sheet(self, symbol: str, period: str = 'annual', limit: int = 5) -> List[Dict[str, Any]]:
        """Get balance sheet"""
        return self.fetch('balance-sheet-statement', {'symbol': symbol, 'period': period, 'limit': limit}) or []
    
    def get_key_metrics(self, symbol: str, period: str = 'annual', limit: int = 5) -> List[Dict[str, Any]]:
        """Get key metrics"""
        return self.fetch('key-metrics', {'symbol': symbol, 'period': period, 'limit': limit}) or []
    
    def get_insider_trading(self, symbol: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get insider trading transactions"""
        return self.fetch('insider-trading', {'symbol': symbol, 'limit': limit}) or []
    
    def get_historical_prices(self, symbol: str, from_date: Optional[str] = None, to_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Get historical price data.
        
        Args:
            symbol: Stock ticker
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)
        
        Returns:
            Dict with 'historical' key containing price data
        """
        params = {'symbol': symbol}
        if from_date:
            params['from'] = from_date
        if to_date:
            params['to'] = to_date
        return self.fetch('historical-price-full', params) or {}


class RedditClient:
    """
    Reddit sentiment client via ApeWisdom API.
    
    Fetch trending stocks and sentiment data from Reddit communities.
    """
    
    BASE_URL = "https://apewisdom.io/api/v1.0"
    
    def __init__(self):
        pass
    
    def get_trending(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get trending stocks from Reddit.
        
        Args:
            limit: Number of stocks to return (default 20)
        
        Returns:
            List of trending stocks with mention counts
        
        Example:
            trending = reddit.get_trending(limit=10)
            for stock in trending:
                print(f"{stock['ticker']}: {stock['mentions']} mentions")
        """
        try:
            url = f"{self.BASE_URL}/filter/all-stocks"
            response = requests.get(url, params={'page': 1}, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            results = data.get('results', [])[:limit]
            return results
        except requests.RequestException as e:
            print(f"❌ Reddit API error: {e}")
            return []
    
    def get_ticker_sentiment(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Get sentiment for a specific ticker.
        
        Args:
            ticker: Stock ticker (e.g., 'GME', 'AAPL')
        
        Returns:
            Sentiment data for the ticker or None if not found
        """
        try:
            url = f"{self.BASE_URL}/filter/all-stocks"
            response = requests.get(url, params={'page': 1}, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            results = data.get('results', [])
            
            # Find the ticker
            for item in results:
                if item.get('ticker', '').upper() == ticker.upper():
                    return item
            
            return None
        except requests.RequestException as e:
            print(f"❌ Reddit API error: {e}")
            return None


class PolygonClient:
    """
    Polygon.io Python client wrapper.
    
    Provides access to the official Polygon Python client (RESTClient).
    See /apis/polygon_api_docs.md for full documentation.
    """
    
    def __init__(self):
        self.api_key = os.getenv('POLYGON_API_KEY', '')
        if not self.api_key:
            print("⚠️ Warning: POLYGON_API_KEY not set in environment")
        
        self._client = None
    
    @property
    def client(self):
        """Lazy load the Polygon RESTClient"""
        if self._client is None:
            try:
                from polygon import RESTClient
                self._client = RESTClient(api_key=self.api_key)
            except ImportError:
                print("⚠️ Warning: polygon-api-client not installed. Install with: pip install polygon-api-client")
                self._client = None
        return self._client
    
    def __getattr__(self, name):
        """
        Proxy all method calls to the underlying Polygon RESTClient.
        
        This allows direct access to all Polygon client methods:
        - polygon.get_aggs(ticker, multiplier, timespan, from_, to)
        - polygon.get_snapshot_ticker(ticker)
        - polygon.get_ticker_details(ticker)
        - polygon.list_tickers(search=None, market='stocks')
        - And many more...
        
        Examples:
            # Get aggregate bars
            aggs = polygon.get_aggs('AAPL', 1, 'day', '2024-01-01', '2024-12-31')
            
            # Get snapshot
            snapshot = polygon.get_snapshot_ticker('stocks', 'AAPL')
            
            # Get ticker details
            details = polygon.get_ticker_details('AAPL')
            
            # Search tickers
            tickers = polygon.list_tickers(search='Apple', limit=10)
        """
        if self.client is None:
            raise RuntimeError("Polygon client not available. Check API key and installation.")
        return getattr(self.client, name)


# Global instances - ready to use
fmp = FMPClient()
reddit = RedditClient()
polygon = PolygonClient()

# Helper functions for common operations
def fetch_multiple_stocks(tickers: List[str], endpoint: str = 'quote') -> Dict[str, Any]:
    """
    Fetch data for multiple tickers efficiently.
    
    Args:
        tickers: List of stock tickers
        endpoint: FMP endpoint to fetch (default: 'quote')
    
    Returns:
        Dict mapping ticker -> data
    
    Example:
        data = fetch_multiple_stocks(['AAPL', 'MSFT', 'GOOGL'], 'quote')
        for ticker, quote in data.items():
            print(f"{ticker}: ${quote['price']}")
    """
    results = {}
    for ticker in tickers:
        result = fmp.fetch(endpoint, {'symbol': ticker})
        if result:
            # Handle both list and dict responses
            if isinstance(result, list) and len(result) > 0:
                results[ticker] = result[0]
            else:
                results[ticker] = result
    return results


def combine_financial_data(symbol: str) -> Dict[str, Any]:
    """
    Fetch comprehensive financial data for a symbol.
    
    Gets quote, income statement, balance sheet, and key metrics.
    All data stays in code - nothing flows through LLM context.
    
    Args:
        symbol: Stock ticker
    
    Returns:
        Dict with all financial data
    
    Example:
        data = combine_financial_data('AAPL')
        print(f"P/E: {data['metrics'][0]['peRatio']}")
        print(f"Revenue: {data['income'][0]['revenue']}")
    """
    return {
        'quote': fmp.get_quote(symbol),
        'income': fmp.get_income_statement(symbol, limit=1),
        'balance': fmp.get_balance_sheet(symbol, limit=1),
        'metrics': fmp.get_key_metrics(symbol, limit=1)
    }

