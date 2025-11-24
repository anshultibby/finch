"""
Financial Modeling Prep API - Simplified Universal Client

MAIN METHOD:
    get_fmp_data(endpoint, params, ...) - Universal method for ALL endpoints

USAGE EXAMPLES:
    # Simple fetch
    await fmp_tools.get_fmp_data("quote", {"symbol": "AAPL"})
    
    # With Pydantic parsing
    await fmp_tools.get_fmp_data("quote", {"symbol": "AAPL"}, model_class=Quote, expect_list=False)
    
    # List data with CSV output
    await fmp_tools.get_fmp_data("income-statement", {"symbol": "AAPL", "period": "annual"}, 
                                  model_class=IncomeStatement)
    
    # Market movers (no params)
    await fmp_tools.get_fmp_data("biggest-gainers")

INVALID PARAMS:
    Invalid query parameters are silently ignored by the FMP API.
    The API will only use parameters it recognizes.
"""
import httpx
import pandas as pd
from models.fmp import (
    CompanyProfile, IncomeStatement, BalanceSheet, CashFlowStatement,
    KeyMetrics, FinancialRatio, HistoricalPrice, Quote,
    AnalystRecommendation, FinancialGrowth
)
from config import Config
from typing import Optional, Dict, Any


# ===================================================================================
# ENDPOINT CATALOG - Documentation of available endpoints and their parameters
# ===================================================================================
ENDPOINTS = {
    # Company Info
    "profile": {
        "params": ["symbol"],
        "model": CompanyProfile,
        "list": False,
        "description": "Get comprehensive company profile and information"
    },
    
    # Financial Statements  
    "income-statement": {
        "params": ["symbol", "period", "limit"],
        "model": IncomeStatement,
        "list": True,
        "description": "Get income statement data (period: annual/quarter)"
    },
    "balance-sheet": {
        "params": ["symbol", "period", "limit"],
        "model": BalanceSheet,
        "list": True,
        "description": "Get balance sheet data"
    },
    "cash-flow-statement": {
        "params": ["symbol", "period", "limit"],
        "model": CashFlowStatement,
        "list": True,
        "description": "Get cash flow statement data"
    },
    
    # Key Metrics & Ratios
    "key-metrics": {
        "params": ["symbol", "period", "limit"],
        "model": KeyMetrics,
        "list": True,
        "description": "Get key metrics and valuation ratios"
    },
    "financial-ratios": {
        "params": ["symbol", "period", "limit"],
        "model": FinancialRatio,
        "list": True,
        "description": "Get financial ratios (liquidity, profitability, etc.)"
    },
    "financial-growth": {
        "params": ["symbol", "period", "limit"],
        "model": FinancialGrowth,
        "list": True,
        "description": "Get financial growth metrics"
    },
    
    # Market Data
    "quote": {
        "params": ["symbol"],
        "model": Quote,
        "list": False,
        "description": "Get real-time quote data"
    },
    "historical-price-full": {
        "params": ["symbol", "from", "to", "limit"],
        "data_key": "historical",
        "model": HistoricalPrice,
        "list": True,
        "path_param": "symbol",  # Symbol goes in URL path
        "description": "Get historical end-of-day prices"
    },
    
    # Analyst Data
    "grade": {
        "params": ["symbol", "limit"],
        "model": AnalystRecommendation,
        "list": True,
        "description": "Get analyst recommendations"
    },
    "price-target-consensus": {
        "params": ["symbol"],
        "description": "Get analyst price target consensus"
    },
    "grades": {
        "params": ["symbol", "limit"],
        "description": "Get analyst upgrades and downgrades"
    },
    
    # Search & Screening
    "search-symbol": {
        "params": ["query", "limit"],
        "description": "Search for stock symbols by query"
    },
    "company-screener": {
        "params": ["marketCapMoreThan", "marketCapLowerThan", "priceMoreThan", 
                   "priceLowerThan", "betaMoreThan", "betaLowerThan", "limit"],
        "description": "Screen stocks based on criteria"
    },
    
    # Market Movers
    "biggest-gainers": {
        "params": [],
        "description": "Get biggest stock gainers"
    },
    "biggest-losers": {
        "params": [],
        "description": "Get biggest stock losers"
    },
    "most-actives": {
        "params": [],
        "description": "Get most actively traded stocks"
    },
    "sector-performance-snapshot": {
        "params": [],
        "description": "Get sector performance"
    },
    
    # News
    "news/stock": {
        "params": ["symbols", "limit"],
        "description": "Get stock news for specific symbols"
    },
    "news/stock-latest": {
        "params": ["page", "limit"],
        "description": "Get latest stock news"
    },
    
    # ETF
    "etf/holdings": {
        "params": ["symbol"],
        "description": "Get ETF holdings"
    },
    "etf/info": {
        "params": ["symbol"],
        "description": "Get ETF information"
    },
    "etf/sector-weightings": {
        "params": ["symbol"],
        "description": "Get ETF sector weightings"
    },
    
    # Corporate Events
    "earnings-calendar": {
        "params": ["from", "to"],
        "description": "Get earnings calendar"
    },
    "dividends-calendar": {
        "params": ["from", "to"],
        "description": "Get dividends calendar"
    },
    "splits": {
        "params": ["symbol"],
        "description": "Get stock split history"
    },
    
    # Economic Data
    "treasury-rates": {
        "params": ["from", "to"],
        "description": "Get treasury rates"
    },
    "economic-indicators": {
        "params": ["name", "from", "to"],
        "description": "Get economic indicator data (GDP, unemployment, etc.)"
    },
    
    # Peers & Comparisons
    "stock-peers": {
        "params": ["symbol"],
        "description": "Get stock peer companies"
    },
    
    # SEC Filings
    "sec-filings-search/symbol": {
        "params": ["symbol", "limit", "from", "to"],
        "description": "Search SEC filings by symbol"
    },
    "sec-filings-search/form-type": {
        "params": ["formType", "limit", "from", "to"],
        "description": "Search SEC filings by form type"
    },
    
    # ESG
    "esg-ratings": {
        "params": ["symbol"],
        "description": "Get ESG (Environmental, Social, Governance) score"
    },
    
    # ============ Insider Trading ============
    "senate-latest": {
        "params": ["page", "limit"],
        "description": "Get recent Senate trading disclosures"
    },
    "house-latest": {
        "params": ["page", "limit"],
        "description": "Get recent House trading disclosures"
    },
    "insider-trading/latest": {
        "params": ["page", "limit"],
        "description": "Get recent corporate insider trades (SEC Form 4)"
    },
    "insider-trading-search": {
        "params": ["symbol", "reportingCik", "companyCik", "transactionType", "limit", "page"],
        "description": "Search insider trades with filters"
    },
    "insider-trading-statistics": {
        "params": ["symbol"],
        "description": "Get quarterly insider trading statistics for a stock"
    },
}


class FMPTools:
    """
    Universal FMP API client.
    
    Use get_fmp_data() for ALL endpoints.
    See ENDPOINTS dict for available endpoints and parameters.
    """
    
    BASE_URL = "https://financialmodelingprep.com/api/v3"
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.api_key = Config.FMP_API_KEY
        self.api_enabled = bool(self.api_key)
    
    async def _fetch_api_data(self, endpoint, params, data_key=None, path_param=None):
        """Low-level method to fetch from API (no streaming events)"""
        if not self.api_enabled:
            raise ValueError(
                "Financial data features require a Financial Modeling Prep API key. "
                "Please add FMP_API_KEY to your .env file. "
                "Get your API key from: https://site.financialmodelingprep.com/developer/docs/pricing"
            )
        
        try:
            # Handle path parameters (e.g., /historical-price-full/SYMBOL)
            path_value = None
            if path_param and path_param in params:
                path_value = params.pop(path_param)
                url = f"{self.BASE_URL}/{endpoint}/{path_value}"
            else:
                url = f"{self.BASE_URL}/{endpoint}"
            
            params["apikey"] = self.api_key
            
            # Build detailed status message with endpoint and key params
            symbol = params.get('symbol', path_value if (path_param == 'symbol' and path_value) else '')
            period = params.get('period', '')
            param_details = []
            if symbol:
                param_details.append(f"symbol={symbol}")
            if period:
                param_details.append(f"period={period}")
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if data_key:
                return data.get(data_key) if isinstance(data, dict) else None
            
            return data
            
        except httpx.HTTPError as e:
            print(f"❌ HTTP error fetching {endpoint}: {str(e)}", flush=True)
            raise
        except Exception as e:
            print(f"❌ Error fetching {endpoint}: {str(e)}", flush=True)
            raise
    
    async def get_fmp_data(
        self,
        endpoint,
        params=None,
        model_class=None,
        expect_list=None,
        result_key=None,
        log_prefix="📊",
        item_name=None
    ):
        """
        *** MAIN METHOD - Use this for ALL FMP endpoints ***
        
        Args:
            endpoint: API endpoint (e.g., "quote", "income-statement", "biggest-gainers")
                     See ENDPOINTS dict for full list
            params: Dict of query parameters (invalid params are ignored by API)
            model_class: Optional Pydantic model for parsing (e.g., Quote, IncomeStatement)
            expect_list: Whether to expect list data (auto-detected if not provided)
            result_key: Optional key name for results (e.g., "quote", "earnings")
            log_prefix: Emoji for logging
            item_name: Name for logging (auto-generated if not provided)
        
        Returns:
            Dict with success, data/data_csv, message, etc.
            - Simple fetch returns: {"success": bool, "data": any, "count": int}
            - With model_class and expect_list=True: {"success": bool, "data_csv": str, "count": int}
            - With model_class and expect_list=False: {"success": bool, "<item_name>": dict}
            
        Examples:
            # Simple fetch (no parsing)
            await get_fmp_data("quote", {"symbol": "AAPL"})
            
            # With Pydantic parsing to CSV
            await get_fmp_data("income-statement", {"symbol": "AAPL", "period": "annual"}, 
                               model_class=IncomeStatement)
            
            # Single item with parsing
            await get_fmp_data("quote", {"symbol": "AAPL"}, model_class=Quote, expect_list=False)
            
            # Market movers (no params)
            await get_fmp_data("biggest-gainers")
        """
        params = params or {}
        
        # Auto-detect settings from ENDPOINTS catalog
        endpoint_info = ENDPOINTS.get(endpoint, {})
        if expect_list is None:
            expect_list = endpoint_info.get("list", True)
        data_key = endpoint_info.get("data_key")
        path_param = endpoint_info.get("path_param")
        if model_class is None:
            model_class = endpoint_info.get("model")
        
        # Use Pydantic parsing if model_class provided
        if model_class:
            return await self._fetch_and_parse(
                endpoint, params, model_class, data_key=data_key,
                path_param=path_param,
                log_prefix=log_prefix, item_name=item_name or endpoint,
                expect_list=expect_list
            )
        
        # Otherwise simple fetch
        try:
            data = await self._fetch_api_data(endpoint, params, data_key, path_param=path_param)
            result = {"success": True}
            
            if result_key:
                result[result_key] = data
            else:
                result["data"] = data
                
            if isinstance(data, list):
                result["count"] = len(data)
            
            # Add symbol if present
            if "symbol" in params:
                result["symbol"] = params["symbol"]
            
            return result
        except Exception as e:
            return {"success": False, "message": f"Failed: {str(e)}"}
    
    async def _fetch_and_parse(
        self,
        endpoint,
        params,
        model_class,
        data_key=None,
        path_param=None,
        log_prefix="📊",
        item_name="items",
        expect_list=True
    ):
        """Parse data using Pydantic models (no streaming events)"""
        # Get symbol before it might be removed by path_param processing
        symbol = params.get("symbol", "N/A")
        period = params.get("period", "")
        limit = params.get("limit", "all available")
        
        try:
            period_str = f"{period} " if period else ""
            limit_str = f" (limit: {limit})" if limit != "all available" else ""
            print(f"{log_prefix} Fetching {period_str}{item_name} for {symbol}...", flush=True)
            
            data = await self._fetch_api_data(endpoint, params, data_key, path_param=path_param)
            
            if not data:
                return {
                    "success": False,
                    "message": f"No {item_name} found for {symbol}"
                }
            
            # Normalize data to list for processing
            data_list = data if isinstance(data, list) else [data]
            total_items = len(data_list)
            
            # Parse using Pydantic models
            parsed_items = []
            failed_items = 0
            for idx, item_data in enumerate(data_list, 1):
                try:
                    item = model_class(**item_data)
                    parsed_items.append(item)
                except Exception as e:
                    print(f"⚠️ Error parsing {item_name} record {idx}: {e}", flush=True)
                    failed_items += 1
                    continue
            
            if not parsed_items:
                return {
                    "success": False,
                    "message": f"Could not parse {item_name} for {symbol}"
                }
            
            # Handle single vs list returns
            if expect_list:
                # Return as CSV for list data
                if hasattr(model_class, 'list_to_df'):
                    df = model_class.list_to_df(parsed_items)
                    data_csv = df.to_csv(index=False)
                    csv_size_kb = len(data_csv) / 1024
                else:
                    # Fallback: convert to dict list
                    df = pd.DataFrame([item.model_dump() for item in parsed_items])
                    data_csv = df.to_csv(index=False)
                    csv_size_kb = len(data_csv) / 1024
                
                print(f"✅ Found {len(parsed_items)} {item_name} for {symbol}", flush=True)
                
                result = {
                    "success": True,
                    "symbol": symbol,
                    "data_csv": data_csv,
                    "count": len(parsed_items),
                    "message": f"Found {len(parsed_items)} {period_str}{item_name} for {symbol}. Data is in CSV format."
                }
                
                if period:
                    result["period"] = period
                
                return result
            else:
                # Return single item as dict
                item = parsed_items[0]
                print(f"✅ Found {item_name} for {symbol}", flush=True)
                
                return {
                    "success": True,
                    "symbol": symbol,
                    item_name.replace(" ", "_"): item.model_dump(),
                    "message": f"Found {item_name} for {symbol}"
                }
            
        except Exception as e:
            print(f"❌ Error fetching {item_name}: {str(e)}", flush=True)
            return {
                "success": False,
                "message": f"Failed to fetch {item_name}: {str(e)}"
            }
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
    
    async def get_fmp_data_streaming(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None
    ):
        """
        Streaming wrapper around get_fmp_data that yields SSE events
        
        For now, it just calls the existing method and yields the final result.
        
        Args:
            endpoint: FMP API endpoint
            params: Query parameters
            
        Yields:
            SSEEvent objects followed by final result dict
        """
        from models.sse import SSEEvent
        
        # Call the existing method (no streaming in internal methods)
        result = await self.get_fmp_data(
            endpoint=endpoint,
            params=params
        )
        
        # Yield final result
        yield result


# Global tools instance
fmp_tools = FMPTools()

