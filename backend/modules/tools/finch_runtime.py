"""
Finch Runtime - Preloaded clients and utilities for code execution

This module is automatically available in all execute_code environments.
It provides direct access to API clients without needing tool calls.

📖 DOCUMENTATION:
- Read this source code to see available clients and their methods
- Read `/apis/*.md` files for detailed API documentation
- Each client class below shows usage examples in docstrings

USAGE:
    from finch_runtime import fmp, reddit, polygon
    
    # See class docstrings below for available methods
    # Or read the API docs: open('apis/get_fmp_data.md').read()
"""
import os
import requests
from typing import Dict, Any, Optional, List


class FMPClient:
    """
    Financial Modeling Prep Python client wrapper.
    
    Provides access to the official FMP Data client (FMPDataClient).
    
    🚨 CRITICAL: The FMP client has a modular structure. You MUST use the correct category.
    
    ✅ CORRECT USAGE:
        fmp.company.get_profile('AAPL')
        fmp.market.get_quote('AAPL')
        fmp.market.get_historical_price('AAPL', from_date='2024-01-01', to_date='2024-12-31')
        fmp.fundamental.get_income_statement('AAPL')  # Note: "fundamental" is SINGULAR
        fmp.insider.get_insider_trading('AAPL')
    
    ❌ COMMON MISTAKES (these DON'T work):
        fmp.get_profile('AAPL')  # NO - must use fmp.company.get_profile()
        fmp.quotes.get_quote('AAPL')  # NO - quotes are under fmp.market.get_quote()
        fmp.historical.get_historical_prices()  # NO - use fmp.market.get_historical_price()
        fmp.fundamentals.*  # NO - it's fmp.fundamental.* (SINGULAR!)
    
    📖 AVAILABLE CATEGORIES (these are the actual attributes):
    - fmp.company: Company profiles, executives, search
        - get_profile(symbol)
        - get_executives(symbol)
        - search(query, limit=10)
        - get_employee_count(symbol)
    
    - fmp.market: Market data, quotes, historical prices, market movers
        - get_quote(symbol)  # Current quote
        - get_historical_price(symbol, from_date, to_date)  # Historical OHLCV
        - get_gainers(limit=20)
        - get_losers(limit=20)
        - get_most_active(limit=20)
    
    - fmp.fundamental: Financial statements and metrics (SINGULAR!)
        - get_income_statement(symbol, period='annual', limit=5)
        - get_balance_sheet(symbol, period='annual', limit=5)
        - get_cash_flow_statement(symbol, period='annual', limit=5)
        - get_key_metrics(symbol, period='annual', limit=5)
        - get_ratios(symbol, period='annual', limit=5)
    
    - fmp.insider: Insider trading data
        - get_insider_trading(symbol, limit=100)
        - get_senate_trading(symbol, limit=100)
        - get_house_trading(symbol, limit=100)
    
    🔍 DISCOVERY: If unsure, explore the client in your code:
        print(dir(fmp.client))  # See all available categories
        print(dir(fmp.company))  # See all methods in a category
    
    All data fetching happens in code - results never flow through LLM context.
    """
    
    def __init__(self):
        self.api_key = os.getenv('FMP_API_KEY', '')
        if not self.api_key:
            print("⚠️ Warning: FMP_API_KEY not set in environment")
        
        self._client = None
    
    @property
    def client(self):
        """Lazy load the FMPDataClient"""
        if self._client is None:
            try:
                from fmp_data import FMPDataClient
                # Create client with minimal configuration
                self._client = FMPDataClient(api_key=self.api_key)
            except ImportError:
                print("⚠️ Warning: fmp-data not installed. Install with: pip install fmp-data")
                self._client = None
        return self._client
    
    def __getattr__(self, name):
        """
        Proxy all attribute/method calls to the underlying FMPDataClient.
        
        This allows you to use fmp.company.get_profile(), fmp.market.get_quote(), etc.
        """
        if self.client is None:
            raise RuntimeError("FMP client not available. Check API key and installation.")
        return getattr(self.client, name)


class RedditClient:
    """
    Reddit sentiment client via ApeWisdom API.
    
    Fetch trending stocks and sentiment data from Reddit communities.
    
    Available methods:
    - get_trending(limit): Get trending stocks
    - get_ticker_sentiment(ticker): Get sentiment for specific ticker
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
            List of trending stocks with mention counts and ranks
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
    
    📖 DOCUMENTATION: Read 'apis/polygon_api_docs.md' for usage examples
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
        
        Common methods:
        - get_aggs(): Aggregate bars (OHLCV)
        - get_snapshot_ticker(): Current snapshot
        - get_ticker_details(): Ticker details
        - list_tickers(): Search tickers
        - get_previous_close_agg(): Previous close
        - get_grouped_daily_aggs(): All stocks for a date
        
        📖 For usage examples, read: open('apis/polygon_api_docs.md').read()
        """
        if self.client is None:
            raise RuntimeError("Polygon client not available. Check API key and installation.")
        return getattr(self.client, name)


# Global instances - ready to use
fmp = FMPClient()
reddit = RedditClient()
polygon = PolygonClient()

