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
    AnalystRecommendation, FinancialGrowth, StockScreenerResult
)
from config import Config
from typing import Optional, Dict, Any, List


# ===================================================================================
# ENDPOINT CATALOG - Documentation of available endpoints and their parameters
# ===================================================================================
ENDPOINTS = {
    # Company Info
    "profile": {
        "params": ["symbol"],
        "model": CompanyProfile,
        "list": False,
        "path_param": "symbol",  # Symbol goes in URL path
        "description": "Get comprehensive company profile and information"
    },
    
    # Financial Statements  
    "income-statement": {
        "params": ["symbol", "period", "limit"],
        "model": IncomeStatement,
        "list": True,
        "path_param": "symbol",  # Symbol goes in URL path
        "description": "Get income statement data (period: annual/quarter)"
    },
    "balance-sheet-statement": {
        "params": ["symbol", "period", "limit"],
        "model": BalanceSheet,
        "list": True,
        "path_param": "symbol",  # Symbol goes in URL path
        "description": "Get balance sheet data"
    },
    "cash-flow-statement": {
        "params": ["symbol", "period", "limit"],
        "model": CashFlowStatement,
        "list": True,
        "path_param": "symbol",  # Symbol goes in URL path
        "description": "Get cash flow statement data"
    },
    
    # Key Metrics & Ratios
    "key-metrics": {
        "params": ["symbol", "period", "limit"],
        "model": KeyMetrics,
        "list": True,
        "path_param": "symbol",  # Symbol goes in URL path
        "description": "Get key metrics and valuation ratios"
    },
    "ratios": {
        "params": ["symbol", "period", "limit"],
        "model": FinancialRatio,
        "list": True,
        "path_param": "symbol",  # Symbol goes in URL path
        "description": "Get financial ratios (liquidity, profitability, etc.)"
    },
    "financial-growth": {
        "params": ["symbol", "period", "limit"],
        "model": FinancialGrowth,
        "list": True,
        "path_param": "symbol",  # Symbol goes in URL path
        "description": "Get financial growth metrics"
    },
    
    # Market Data
    "quote": {
        "params": ["symbol"],
        "model": Quote,
        "list": False,
        "path_param": "symbol",  # Symbol goes in URL path
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
        "path_param": "symbol",  # Symbol goes in URL path
        "description": "Get analyst recommendations"
    },
    "price-target-consensus": {
        "params": ["symbol"],
        "path_param": "symbol",  # Symbol goes in URL path
        "description": "Get analyst price target consensus"
    },
    "grades": {
        "params": ["symbol", "limit"],
        "path_param": "symbol",  # Symbol goes in URL path
        "description": "Get analyst upgrades and downgrades"
    },
    
    # Search & Screening
    "search-symbol": {
        "params": ["query", "limit"],
        "description": "Search for stock symbols by query"
    },
    "company-screener": {
        "params": [
            "marketCapMoreThan", "marketCapLowerThan", 
            "sector", "industry",
            "betaMoreThan", "betaLowerThan",
            "priceMoreThan", "priceLowerThan",
            "dividendMoreThan", "dividendLowerThan",
            "volumeMoreThan", "volumeLowerThan",
            "exchange", "country",
            "isEtf", "isFund", "isActivelyTrading",
            "limit", "includeAllShareClasses"
        ],
        "model": StockScreenerResult,
        "list": True,
        "description": "Screen stocks based on market cap, price, volume, sector, industry, and more"
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
        "path_param": "symbol",  # Symbol goes in URL path
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
        "path_param": "symbol",  # Symbol goes in URL path
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
        "path_param": "symbol",  # Symbol goes in URL path
        "description": "Get ESG (Environmental, Social, Governance) score"
    },
    
    # ============ Insider Trading (v4 API) ============
    "insider-trading": {
        "params": ["symbol", "reportingCik", "companyCik", "transactionType", "limit", "page"],
        "description": "Search insider trades with filters (v4 endpoint)",
        "api_version": "v4"
    },
    "insider-roster": {
        "params": ["symbol"],
        "description": "Get list of insiders for a company (v4 endpoint)",
        "api_version": "v4"
    },
    
    # ============ Government Trading (v4 API) ============
    "senate-trading": {
        "params": ["symbol", "limit"],
        "description": "Get Senate stock trading disclosures for a symbol (v4 endpoint)",
        "api_version": "v4"
    },
    "house-trading": {
        "params": ["symbol", "limit"],
        "description": "Get House of Representatives stock trading disclosures for a symbol (v4 endpoint)",
        "api_version": "v4"
    },
}


class FMPTools:
    """
    Universal FMP API client.
    
    Use get_fmp_data() for ALL endpoints.
    See ENDPOINTS dict for available endpoints and parameters.
    """
    
    BASE_URL = "https://financialmodelingprep.com/api/v3"
    BASE_URL_V4 = "https://financialmodelingprep.com/api/v4"
    
    def __init__(self):
        self._client = None
        self.api_key = Config.FMP_API_KEY
        self.api_enabled = bool(self.api_key)
    
    @property
    def client(self):
        """Lazy-load HTTP client to avoid event loop issues"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client
    
    async def _fetch_api_data(self, endpoint, params, data_key=None, path_param=None, api_version=None):
        """Low-level method to fetch from API (no streaming events)"""
        if not self.api_enabled:
            raise ValueError(
                "Financial data features require a Financial Modeling Prep API key. "
                "Please add FMP_API_KEY to your .env file. "
                "Get your API key from: https://site.financialmodelingprep.com/developer/docs/pricing"
            )
        
        try:
            # Choose base URL based on API version
            base_url = self.BASE_URL_V4 if api_version == "v4" else self.BASE_URL
            
            # Handle path parameters (e.g., /historical-price-full/SYMBOL)
            path_value = None
            if path_param and path_param in params:
                path_value = params.pop(path_param)
                url = f"{base_url}/{endpoint}/{path_value}"
            else:
                url = f"{base_url}/{endpoint}"
            
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
            
            # Log what we received for debugging
            import logging
            logger = logging.getLogger(__name__)
            data_type = type(data).__name__
            data_size = len(data) if isinstance(data, (list, dict)) else "N/A"
            logger.info(f"📦 HTTP Response: {data_type} size={data_size} endpoint={endpoint} data_key={data_key}")
            
            # Show sample if it's a list
            if isinstance(data, list):
                if data:
                    logger.info(f"   ✅ List has {len(data)} items, first keys: {list(data[0].keys())[:10] if isinstance(data[0], dict) else 'N/A'}")
                else:
                    logger.warning(f"   ⚠️  Empty list returned from API")
            
            # Handle data_key extraction
            if data_key:
                logger.info(f"   Extracting data_key='{data_key}' from {data_type}")
                extracted = data.get(data_key) if isinstance(data, dict) else None
                logger.info(f"   Result after extraction: {type(extracted).__name__ if extracted else 'None'}")
                return extracted
            
            logger.info(f"   ✅ Returning data as-is")
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
        api_version = endpoint_info.get("api_version")  # Get API version (v3 or v4)
        if model_class is None:
            model_class = endpoint_info.get("model")
        
        # Use Pydantic parsing if model_class provided
        if model_class:
            return await self._fetch_and_parse(
                endpoint, params, model_class, data_key=data_key,
                path_param=path_param, api_version=api_version,
                log_prefix=log_prefix, item_name=item_name or endpoint,
                expect_list=expect_list
            )
        
        # Otherwise simple fetch (no model parsing)
        try:
            data = await self._fetch_api_data(endpoint, params, data_key, path_param=path_param, api_version=api_version)
            
            # Simple success check
            success = bool(data) and (not isinstance(data, list) or len(data) > 0)
            
            result = {
                "success": success,
                "data": data if data is not None else []
            }
                
            if isinstance(data, list):
                result["count"] = len(data)
            
            # Add symbol if present
            if "symbol" in params:
                result["symbol"] = params["symbol"]
            
            # Add helpful error message if no data
            if not success:
                symbol = params.get("symbol", "unknown")
                result["message"] = f"No data found for {symbol}"
            
            return result
        except Exception as e:
            return {
                "success": False, 
                "message": f"Failed: {str(e)}",
                "data": []
            }
    
    async def _fetch_and_parse(
        self,
        endpoint,
        params,
        model_class,
        data_key=None,
        path_param=None,
        api_version=None,
        log_prefix="📊",
        item_name="items",
        expect_list=True
    ):
        """Parse data using Pydantic models - always returns 'data' key"""
        # Get symbol before it might be removed by path_param processing
        symbol = params.get("symbol", "N/A")
        period = params.get("period", "")
        limit = params.get("limit", "all available")
        
        try:
            period_str = f"{period} " if period else ""
            print(f"{log_prefix} Fetching {period_str}{item_name} for {symbol}...", flush=True)
            
            data = await self._fetch_api_data(endpoint, params, data_key, path_param=path_param, api_version=api_version)
            
            # Simple check: is there any data?
            if not data:  # Handles None, [], {}, "", 0, False
                return {
                    "success": False,
                    "message": f"No {item_name} found for {symbol}",
                    "data": []
                }
            
            # Normalize data to list for processing
            data_list = data if isinstance(data, list) else [data]
            
            # Parse using Pydantic models
            parsed_items = []
            for idx, item_data in enumerate(data_list, 1):
                try:
                    item = model_class(**item_data)
                    parsed_items.append(item.model_dump())
                except Exception as e:
                    print(f"⚠️ Error parsing {item_name} record {idx}: {e}", flush=True)
                    continue
            
            if not parsed_items:
                return {
                    "success": False,
                    "message": f"Could not parse {item_name} for {symbol}",
                    "data": []
                }
            
            print(f"✅ Found {len(parsed_items)} {item_name} for {symbol}", flush=True)
            
            # Always return data as list for consistency (single item is a list of 1)
            result = {
                "success": True,
                "data": parsed_items,
                "count": len(parsed_items)
            }
            
            if symbol != "N/A":
                result["symbol"] = symbol
            
            if period:
                result["period"] = period
            
            return result
            
        except Exception as e:
            print(f"❌ Error fetching {item_name}: {str(e)}", flush=True)
            return {
                "success": False,
                "message": f"Failed to fetch {item_name}: {str(e)}",
                "data": []
            }
    
    async def close(self):
        """Close the HTTP client"""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
    
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


# ============================================================================
# CANDIDATE LISTS - Get stock universes for screening
# ============================================================================
# FMP Endpoints (verified):
# /api/v3/sp500_constituent
# /api/v3/nasdaq_constituent  
# /api/v3/dowjones_constituent

async def get_sp500_tickers() -> List[str]:
    """
    Get all S&P 500 tickers from FMP
    
    Raises:
        Exception: If API call fails
    """
    data = await fmp_tools._fetch_api_data("sp500_constituent", {})
    if not data:
        raise ValueError("No S&P 500 data returned from FMP")
    return [item.get("symbol") for item in data if item.get("symbol")]


async def get_nasdaq100_tickers() -> List[str]:
    """
    Get all NASDAQ 100 tickers from FMP
    
    Raises:
        Exception: If API call fails
    """
    data = await fmp_tools._fetch_api_data("nasdaq_constituent", {})
    if not data:
        raise ValueError("No NASDAQ data returned from FMP")
    return [item.get("symbol") for item in data if item.get("symbol")]


async def get_dow30_tickers() -> List[str]:
    """
    Get all Dow Jones 30 tickers from FMP
    
    Raises:
        Exception: If API call fails
    """
    data = await fmp_tools._fetch_api_data("dowjones_constituent", {})
    if not data:
        raise ValueError("No Dow Jones data returned from FMP")
    return [item.get("symbol") for item in data if item.get("symbol")]


async def get_candidates_from_source(candidate_source: dict) -> List[str]:
    """
    Get candidate tickers based on source configuration
    
    Args:
        candidate_source: Dict with type, universe, tickers, etc.
        
    Returns:
        List of ticker symbols
        
    Raises:
        ValueError: If source configuration is invalid
        Exception: If API calls fail
    """
    source_type = candidate_source.get("type")
    if not source_type:
        raise ValueError("candidate_source must have 'type' field")
    
    if source_type == "universe":
        universe = candidate_source.get("universe", "sp500")
        if universe == "sp500":
            return await get_sp500_tickers()
        elif universe == "nasdaq100":
            return await get_nasdaq100_tickers()
        elif universe == "dow30":
            return await get_dow30_tickers()
        else:
            raise ValueError(f"Unknown universe: {universe}. Use sp500, nasdaq100, or dow30")
    
    elif source_type in ["custom", "tickers"]:  # Both mean the same thing
        tickers = candidate_source.get("tickers")
        if not tickers:
            raise ValueError("custom/tickers source type requires 'tickers' list")
        return tickers
    
    elif source_type == "reddit_trending":
        from modules.tools.definitions import tool_registry
        reddit_tool = tool_registry.get_tool("get_reddit_trending_stocks")
        if not reddit_tool:
            raise ValueError("Reddit trending tool not available")
        
        limit = candidate_source.get("limit", 50)
        result = await reddit_tool.handler(limit=limit)
        
        if not result.get("success"):
            raise ValueError(f"Reddit API failed: {result.get('error', 'Unknown error')}")
        
        if "tickers" not in result:
            raise ValueError("Reddit API returned no tickers")
        
        return result["tickers"][:limit]
    
    else:
        raise ValueError(f"Unknown candidate source type: {source_type}")

